INSERT INTO users (username, password, email, signature, level) VALUES
('同学A', '123456', 'student@example.com', '愿你在书页间，遇见更好的自己。', '普通用户');

INSERT INTO books (title, author, price, category, publisher, isbn, format, stock_type, stock_text, description) VALUES
('Digital Fundamentals', 'Thomas L. Floyd', 59, '电子技术 / 数字电路', 'Pearson', '978-0-00-000000-1', '电子书 · 立即阅读', 'ok', '有货', '以数字电子技术为主线，系统介绍逻辑门、组合与时序电路、编码与计数等核心内容。'),
('Fundamentals of Computer Graphics', 'Steve Marschner', 88, '计算机图形学', 'A K Peters/CRC Press', '978-1-00-000000-2', '电子书 · 立即阅读', 'ok', '有货', '介绍现代计算机图形学基础，从几何变换到光照模型与光线追踪。'),
('Introduction To Algorithms', 'Thomas H. Cormen', 99, '算法', 'MIT Press', '978-3-00-000000-4', '电子书 · 立即阅读', 'ok', '有货', '经典算法教材，系统覆盖分治、动态规划、贪心、图算法等核心主题。'),
('深入理解计算机系统', '兰德尔·E·布莱恩特 / 大卫·R·奥哈拉伦', 86, '计算机系统', '机械工业出版社', '978-6-00-000000-7', '电子书 · 立即阅读', 'warn', '库存紧张', '从程序员视角解释计算机系统，涵盖机器级表示、链接、异常、并发和网络。');
