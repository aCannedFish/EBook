import { Button, Form, Input, InputNumber, Modal, Space, Tag, Typography } from "antd";
import { useState } from "react";
import { useLoaderData, useSubmit } from "react-router-dom";
import ResourceTable from "../components/ResourceTable";
import RowActions from "../components/RowActions";
import { ensureBooksLoaded, removeBook, saveBook, setPageSearch } from "../data/appStore";
import { requireAdminSnapshot } from "../routes/authRouteHandlers";

const emptyBook = {
  title: "",
  author: "",
  price: 0,
  category: "",
  publisher: "",
  isbn: "",
  format: "电子书 · 立即阅读",
  stockQty: 0,
  coverUrl: "",
  description: ""
};

export async function adminBooksLoader() {
  requireAdminSnapshot();
  await ensureBooksLoaded();
  const snapshot = requireAdminSnapshot();
  return {
    books: snapshot.books,
    search: snapshot.searchByPage.adminBooks
  };
}

export async function adminBooksAction({ request }) {
  requireAdminSnapshot();
  const formData = await request.formData();
  const intent = String(formData.get("intent") || "");

  if (intent === "set-search") {
    setPageSearch("adminBooks", String(formData.get("value") || ""));
    return null;
  }

  if (intent === "save-book") {
    const bookId = String(formData.get("bookId") || "");
    const payload = {
      title: String(formData.get("title") || ""),
      author: String(formData.get("author") || ""),
      price: Number(formData.get("price") || 0),
      category: String(formData.get("category") || ""),
      publisher: String(formData.get("publisher") || ""),
      isbn: String(formData.get("isbn") || ""),
      format: String(formData.get("format") || "电子书 · 立即阅读"),
      stockQty: Number(formData.get("stockQty") || 0),
      coverUrl: String(formData.get("coverUrl") || ""),
      description: String(formData.get("description") || "")
    };
    await saveBook(payload, bookId || null);
    return null;
  }

  if (intent === "delete-book") {
    const bookId = String(formData.get("bookId") || "");
    if (bookId) {
      await removeBook(bookId);
    }
    return null;
  }

  return null;
}

function AdminBooksPage({ books, search, onSave, onDelete }) {
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form] = Form.useForm();
  const keyword = search.trim().toLowerCase();
  const rows = books.filter((book) => !keyword || book.title.toLowerCase().includes(keyword));

  const openEditor = (book) => {
    setEditing(book);
    form.setFieldsValue(book || emptyBook);
    setOpen(true);
  };

  const columns = [
    {
      title: "封面",
      dataIndex: "cover",
      render: (cover, row) => (
        <img src={cover} alt={row.title} width={48} height={64} style={{ objectFit: "cover" }} />
      )
    },
    { title: "书名", dataIndex: "title" },
    { title: "作者", dataIndex: "author" },
    { title: "ISBN", dataIndex: "isbn" },
    {
      title: "库存",
      dataIndex: "stockQty",
      render: (qty, row) => (
        <Space direction="vertical" size={0}>
          <strong>{qty}</strong>
          <Tag color={row.stockType === "ok" ? "green" : row.stockType === "warn" ? "orange" : "red"}>
            {row.stockText}
          </Tag>
        </Space>
      )
    },
    {
      title: "操作",
      render: (_, row) => (
        <RowActions
          actions={[
            { key: "edit", label: "编辑", onClick: () => openEditor(row) },
            { key: "delete", label: "删除", danger: true, onClick: () => onDelete(row.id) }
          ]}
        />
      )
    }
  ];

  return (
    <section className="page card" aria-label="书籍管理页面">
      <header className="page__header">
        <Typography.Title level={3} className="page__title">书籍管理</Typography.Title>
        <Button type="primary" onClick={() => openEditor(null)}>新增图书</Button>
      </header>
      <ResourceTable rowKey="id" dataSource={rows} columns={columns} />

      <Modal
        title={editing ? "编辑图书" : "新增图书"}
        open={open}
        onCancel={() => setOpen(false)}
        onOk={() => {
          form.validateFields().then((values) => {
            onSave({ ...values, bookId: editing?.id || "" });
            setOpen(false);
          });
        }}
        width={720}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="title" label="书名" rules={[{ required: true, message: "请输入书名" }]}>
            <Input />
          </Form.Item>
          <Form.Item name="author" label="作者" rules={[{ required: true, message: "请输入作者" }]}>
            <Input />
          </Form.Item>
          <Space size={16} style={{ display: "flex" }}>
            <Form.Item name="price" label="定价" rules={[{ required: true }]}>
              <InputNumber min={0} style={{ width: 120 }} />
            </Form.Item>
            <Form.Item name="stockQty" label="库存量" rules={[{ required: true }]}>
              <InputNumber min={0} style={{ width: 120 }} />
            </Form.Item>
          </Space>
          <Form.Item name="isbn" label="ISBN" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="coverUrl" label="封面 URL">
            <Input placeholder="/assets/..." />
          </Form.Item>
          <Form.Item name="category" label="分类" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="publisher" label="出版社" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="format" label="售卖形式" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="简介" rules={[{ required: true }]}>
            <Input.TextArea rows={4} />
          </Form.Item>
        </Form>
      </Modal>
    </section>
  );
}

export function AdminBooksRoute() {
  const data = useLoaderData();
  const submit = useSubmit();

  return (
    <AdminBooksPage
      books={data.books}
      search={data.search}
      onSave={(values) => submit({ intent: "save-book", ...values }, { method: "post", navigate: false })}
      onDelete={(bookId) => submit({ intent: "delete-book", bookId }, { method: "post", navigate: false })}
    />
  );
}

export default AdminBooksPage;
