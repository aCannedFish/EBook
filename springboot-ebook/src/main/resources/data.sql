INSERT INTO users (username, password, email, signature, level) VALUES
('DefaultUser', '123456', 'student@example.com', '愿你在书页间，遇见更好的自己。', '普通用户');

INSERT INTO books (title, author, price, category, publisher, isbn, format, stock_type, stock_text, description) VALUES
('Digital Fundamentals', 'Thomas L. Floyd', 59, '电子技术 / 数字电路', 'Pearson', '978-0-00-000000-1', '电子书 · 立即阅读', 'ok', '有货', '以数字电子技术为主线，系统介绍逻辑门、组合与时序电路、编码与计数等核心内容，适合作为电子与计算机相关专业的入门教材。'),
('Fundamentals of Computer Graphics', 'Steve Marschner', 88, '计算机图形学', 'A K Peters/CRC Press', '978-1-00-000000-2', '电子书 · 立即阅读', 'ok', '有货', '介绍现代计算机图形学基础，从几何变换到光照模型与光线追踪，覆盖课程核心知识。'),
('Intorduction to Computing Systems', 'Yale N. Patt', 79, '计算机系统导论', 'McGraw-Hill', '978-2-00-000000-3', '电子书 · 立即阅读', 'warn', '库存紧张', '通过体系化章节介绍硬件、指令系统与软件协作机制，帮助理解计算机系统全貌。'),
('Introduction To Algorithms', 'Thomas H. Cormen', 99, '算法', 'MIT Press', '978-3-00-000000-4', '电子书 · 立即阅读', 'ok', '有货', '经典算法教材，系统覆盖分治、动态规划、贪心、图算法等高频核心主题。'),
('Qt 6 C++开发指南', '王维波', 68, 'C++ / Qt', '电子工业出版社', '978-4-00-000000-5', '电子书 · 立即阅读', 'ok', '有货', '从 Qt 6 基础组件到项目实战，覆盖界面开发、信号槽与工程组织方法。'),
('应用随机过程', '熊德文', 56, '数学 / 概率', '高等教育出版社', '978-5-00-000000-6', '电子书 · 立即阅读', 'ok', '有货', '围绕马尔可夫链、泊松过程和布朗运动等内容，适用于概率论与工程应用学习。'),
('深入理解计算机系统', '兰德尔·E·布莱恩特 / 大卫·R·奥哈拉伦', 86, '计算机系统', '机械工业出版社', '978-6-00-000000-7', '电子书 · 立即阅读', 'warn', '库存紧张', '从程序员视角解释计算机系统，涵盖机器级表示、链接、异常、并发和网络。'),
('量子物理', '吕智国', 72, '物理', '科学出版社', '978-7-00-000000-8', '电子书 · 立即阅读', 'ok', '有货', '面向初学者梳理量子理论基础概念，配合实例帮助理解微观世界规律。');

INSERT INTO cart_items (user_id, book_id, qty, selected) VALUES
(1, 1, 1, TRUE),
(1, 3, 2, TRUE);

INSERT INTO orders (order_no, user_id, status) VALUES
('ORD-20260519-0001', 1, 'paid'),
('ORD-20260519-0002', 1, 'pending');

INSERT INTO order_items (order_id, book_id, qty, unit_price) VALUES
(1, 2, 1, 88),
(1, 4, 1, 99),
(2, 1, 1, 59),
(2, 3, 2, 79);
