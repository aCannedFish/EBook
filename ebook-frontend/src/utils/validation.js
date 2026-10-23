const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/** 校验邮箱格式。 */
export function isValidEmail(email) {
  return EMAIL_PATTERN.test(String(email || "").trim());
}

/** 校验注册表单：用户名、密码、重复密码、邮箱。 */
export function validateRegisterForm({ username, password, confirmPassword, email }) {
  if (!username?.trim()) {
    return "用户名不能为空。";
  }
  if (!password?.trim()) {
    return "密码不能为空。";
  }
  if (password !== confirmPassword) {
    return "两次输入的密码不一致。";
  }
  if (!email?.trim()) {
    return "邮箱不能为空。";
  }
  if (!isValidEmail(email)) {
    return "邮箱格式不正确。";
  }
  return null;
}

/** 校验登录表单。 */
export function validateLoginForm({ username, password }) {
  if (!username?.trim() || !password?.trim()) {
    return "请输入用户名和密码。";
  }
  return null;
}
