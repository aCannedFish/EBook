/**
 * 管理当前用户的会话列表、快照与实时订阅。
 * URL 保存选中的会话，消息始终以服务端为准；卸载时只关闭订阅，后台问答继续。
 */
import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  createAssistantSession,
  fetchAssistantSession,
  fetchAssistantSessions,
  sendSessionMessage,
  watchAssistantSession
} from "../api/assistantApi";

function updateList(previous, session) {
  const summary = {
    id: session.id,
    title: session.title,
    createdAt: session.createdAt,
    updatedAt: session.updatedAt
  };
  return [summary, ...previous.filter((item) => item.id !== summary.id)]
    .sort((left, right) => right.updatedAt.localeCompare(left.updatedAt));
}

/** 等待重连时也响应卸载，避免离开页面后继续产生请求。 */
function reconnectDelay(signal) {
  return new Promise((resolve) => {
    const finish = () => {
      clearTimeout(timer);
      signal.removeEventListener("abort", finish);
      resolve();
    };
    const timer = setTimeout(finish, 1500);
    signal.addEventListener("abort", finish, { once: true });
    if (signal.aborted) {
      finish();
    }
  });
}

export function useAssistantSessions() {
  const [params, setParams] = useSearchParams();
  const sessionId = params.get("session") || "";
  const [sessions, setSessions] = useState([]);
  const [session, setSession] = useState(null);
  const [listLoading, setListLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const [connectionError, setConnectionError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);
  const mounted = useRef(false);
  const selected = useRef(sessionId);
  const submitting = useRef(false);
  selected.current = sessionId;

  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setListLoading(true);
    fetchAssistantSessions(controller.signal).then((result) => {
      if (controller.signal.aborted) {
        return;
      }
      setSessions(result.sessions);
      if (!selected.current && result.sessions.length) {
        setParams({ session: result.sessions[0].id }, { replace: true });
      }
    }).catch((failure) => {
      if (!controller.signal.aborted) {
        setError(failure.message);
      }
    }).finally(() => {
      if (!controller.signal.aborted) {
        setListLoading(false);
      }
    });
    return () => controller.abort();
  // 列表只在挂载或重试时加载；当前选择通过 selected 引用读取。
  }, [reloadKey]);

  useEffect(() => {
    const controller = new AbortController();
    setError(null);
    setConnectionError(null);
    setSession((previous) => previous?.id === sessionId ? previous : null);
    if (!sessionId) {
      setDetailLoading(false);
      return () => controller.abort();
    }
    setDetailLoading(true);
    fetchAssistantSession(sessionId, controller.signal).then((snapshot) => {
      if (!controller.signal.aborted) {
        setSession(snapshot);
        setSessions((previous) => updateList(previous, snapshot));
      }
    }).catch((failure) => {
      if (!controller.signal.aborted) {
        setError(failure.message);
      }
    }).finally(() => {
      if (!controller.signal.aborted) {
        setDetailLoading(false);
      }
    });
    return () => controller.abort();
  }, [sessionId, reloadKey]);

  const current = session?.id === sessionId ? session : null;
  const messages = current?.messages || [];
  const activeMessage = messages.find((message) => message.status === "running");
  const activeId = detailLoading ? null : activeMessage?.id;

  useEffect(() => {
    if (!activeId) {
      return;
    }
    const controller = new AbortController();
    let cursor = current.cursor;
    let finished = false;

    function applySnapshot(snapshot) {
      cursor = snapshot.cursor;
      setSession(snapshot);
      return !snapshot.messages.some(
        (message) => message.id === activeId && message.status === "running"
      );
    }

    async function subscribe() {
      while (!controller.signal.aborted && !finished) {
        try {
          await watchAssistantSession(sessionId, cursor, (event, eventId) => {
            if (controller.signal.aborted || eventId <= cursor) {
              return;
            }
            cursor = eventId;
            finished = event.message.id === activeId && event.message.status &&
              event.message.status !== "running";
            setConnectionError(null);
            setSession((previous) => {
              if (previous?.id !== sessionId) {
                return previous;
              }
              return {
                ...previous,
                cursor,
                updatedAt: event.updatedAt,
                messages: previous.messages.map((message) =>
                  message.id === event.message.id ? { ...message, ...event.message } : message
                )
              };
            });
          }, controller.signal);
          // SSE 以 done 正常结束：通常是任务完成，用一次快照确认即可，
          // 不要当成断线，否则每次回答结束都会短暂弹出“连接中断”。
          if (finished) {
            return;
          }
          const snapshot = await fetchAssistantSession(sessionId, controller.signal);
          if (controller.signal.aborted) {
            return;
          }
          finished = applySnapshot(snapshot);
          if (!finished) {
            await reconnectDelay(controller.signal);
          }
        } catch (failure) {
          if (controller.signal.aborted) {
            return;
          }
          setConnectionError("进度连接中断，正在自动恢复。查询会在服务端继续执行。");
          await reconnectDelay(controller.signal);
          if (controller.signal.aborted) {
            return;
          }
          try {
            const snapshot = await fetchAssistantSession(sessionId, controller.signal);
            if (controller.signal.aborted) {
              return;
            }
            finished = applySnapshot(snapshot);
            setConnectionError(null);
          } catch {
            // 服务仍不可达时保留已收到的步骤，下一轮继续按游标连接。
          }
        }
      }
    }
    subscribe();
    return () => controller.abort();
  }, [sessionId, activeId]);

  /** 发送期间仅锁住创建/发送操作，不阻止切页；返回后重新读取持久化快照。 */
  async function send(question) {
    if (submitting.current || activeMessage) {
      return false;
    }
    const originalId = sessionId;
    submitting.current = true;
    setSending(true);
    setError(null);
    try {
      const target = sessionId || (await createAssistantSession()).id;
      const snapshot = await sendSessionMessage(target, question);
      if (mounted.current && selected.current === originalId) {
        setSession(snapshot);
        setSessions((previous) => updateList(previous, snapshot));
        setParams({ session: target });
      }
      return true;
    } catch (failure) {
      if (mounted.current && selected.current === originalId) {
        setError(failure.message);
        // 请求响应丢失时，问题可能已经被服务端接收；先恢复快照，避免重复发送。
        if (originalId) {
          try {
            const snapshot = await fetchAssistantSession(originalId);
            if (mounted.current && selected.current === originalId) {
              setSession(snapshot);
            }
          } catch {
            // 保留原错误，用户可以显式重新加载。
          }
        }
      }
      return false;
    } finally {
      submitting.current = false;
      if (mounted.current) {
        setSending(false);
      }
    }
  }

  async function create() {
    if (submitting.current) {
      return;
    }
    submitting.current = true;
    setSending(true);
    try {
      const snapshot = await createAssistantSession();
      if (mounted.current) {
        setSession(snapshot);
        setSessions((previous) => updateList(previous, snapshot));
        setParams({ session: snapshot.id });
      }
    } catch (failure) {
      if (mounted.current) {
        setError(failure.message);
      }
    } finally {
      submitting.current = false;
      if (mounted.current) {
        setSending(false);
      }
    }
  }

  return {
    sessions, sessionId, session: current, messages, activeMessage, sending,
    loading: listLoading || detailLoading, error, connectionError,
    select: (id) => setParams({ session: id }), create, send,
    reload: () => setReloadKey((value) => value + 1)
  };
}
