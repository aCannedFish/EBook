INSERT INTO users (username, password, email, signature, level, enabled) VALUES
('admin', 'admin123', 'admin@example.com', '系统管理员', '管理员', TRUE),
('DefaultUser', '123456', 'student@example.com', '愿你在书页间，遇见更好的自己。', '普通用户', TRUE);

INSERT INTO books (title, author, price, category, publisher, isbn, format, stock_type, stock_text, stock_qty, cover_url, description) VALUES
('Digital Fundamentals', 'Thomas L. Floyd', 59, '电子技术 / 数字电路', 'Pearson', '978-0-00-000000-1', '电子书 · 立即阅读', 'ok', '有货', 50, '/assets/Digital%20Fundamentals%EF%BC%88Thomas.L.Floyd%EF%BC%89.png', '以数字电子技术为主线，系统介绍逻辑门、组合与时序电路、编码与计数等核心内容，适合作为电子与计算机相关专业的入门教材。'),
('Fundamentals of Computer Graphics', 'Steve Marschner', 88, '计算机图形学', 'A K Peters/CRC Press', '978-1-00-000000-2', '电子书 · 立即阅读', 'ok', '有货', 40, '/assets/Fundamentals%20of%20Computer%20Graphics%EF%BC%88Steve%20Marschner%EF%BC%89.png', '介绍现代计算机图形学基础，从几何变换到光照模型与光线追踪，覆盖课程核心知识。'),
('Intorduction to Computing Systems', 'Yale N. Patt', 79, '计算机系统导论', 'McGraw-Hill', '978-2-00-000000-3', '电子书 · 立即阅读', 'warn', '库存紧张', 4, '/assets/Intorduction%20to%20Computing%20Systems%EF%BC%88Yale.N.Patt%EF%BC%89.png', '通过体系化章节介绍硬件、指令系统与软件协作机制，帮助理解计算机系统全貌。'),
('Introduction To Algorithms', 'Thomas H. Cormen', 99, '算法', 'MIT Press', '978-3-00-000000-4', '电子书 · 立即阅读', 'ok', '有货', 30, '/assets/Introduction%20To%20Algorithms%EF%BC%88Thomas.H.Cormen%EF%BC%89.png', '经典算法教材，系统覆盖分治、动态规划、贪心、图算法等高频核心主题。'),
('Qt 6 C++开发指南', '王维波', 68, 'C++ / Qt', '电子工业出版社', '978-4-00-000000-5', '电子书 · 立即阅读', 'ok', '有货', 25, '/assets/Qt%206%20C%2B%2B%E5%BC%80%E5%8F%91%E6%8C%87%E5%8D%97%EF%BC%88%E7%8E%8B%E7%BB%B4%E6%B3%A2%EF%BC%89.png', '从 Qt 6 基础组件到项目实战，覆盖界面开发、信号槽与工程组织方法。'),
('应用随机过程', '熊德文', 56, '数学 / 概率', '高等教育出版社', '978-5-00-000000-6', '电子书 · 立即阅读', 'ok', '有货', 20, '/assets/%E5%BA%94%E7%94%A8%E9%9A%8F%E6%9C%BA%E8%BF%87%E7%A8%8B%EF%BC%88%E7%86%8A%E5%BE%B7%E6%96%87%EF%BC%89.png', '围绕马尔可夫链、泊松过程和布朗运动等内容，适用于概率论与工程应用学习。'),
('深入理解计算机系统', '兰德尔·E·布莱恩特 / 大卫·R·奥哈拉伦', 86, '计算机系统', '机械工业出版社', '978-6-00-000000-7', '电子书 · 立即阅读', 'warn', '库存紧张', 3, '/assets/%E6%B7%B1%E5%85%A5%E7%90%86%E8%A7%A3%E8%AE%A1%E7%AE%97%E6%9C%BA%E7%B3%BB%E7%BB%9F%EF%BC%88%E5%85%B0%E5%BE%B7%E5%B0%94.E.%E5%B8%83%E8%8E%B1%E6%81%A9%E7%89%B9%EF%BC%8C%E5%A4%A7%E5%8D%AB.R.%E5%A5%A5%E5%93%88%E6%8B%89%E4%BC%A6%EF%BC%89.png', '从程序员视角解释计算机系统，涵盖机器级表示、链接、异常、并发和网络。'),
('量子物理', '吕智国', 72, '物理', '科学出版社', '978-7-00-000000-8', '电子书 · 立即阅读', 'ok', '有货', 15, '/assets/%E9%87%8F%E5%AD%90%E7%89%A9%E7%90%86%EF%BC%88%E5%90%95%E6%99%BA%E5%9B%BD%EF%BC%89.png', '面向初学者梳理量子理论基础概念，配合实例帮助理解微观世界规律。');

INSERT INTO cart_items (user_id, book_id, qty, selected) VALUES
(2, 1, 1, TRUE),
(2, 3, 2, TRUE);

INSERT INTO orders (order_no, user_id, status) VALUES
('ORD-20260519-0001', 2, 'paid'),
('ORD-20260519-0002', 2, 'pending');

INSERT INTO order_items (order_id, book_id, qty, unit_price) VALUES
(1, 2, 1, 88),
(1, 4, 1, 99),
(2, 1, 1, 59),
(2, 3, 2, 79);

-- 导购演示书目也属于书城数据库，库存与页面和 Function Calling 工具共用。
INSERT INTO books (title, author, price, category, publisher, isbn, format, stock_type, stock_text, stock_qty, cover_url, description) VALUES
('微服务架构设计模式', 'Chris Richardson', 129, '软件架构', '机械工业出版社', '9787111600001', '纸质书', 'ok', '有货', 16, '/assets/microservices-patterns-zh.png', '介绍服务拆分、分布式事务和微服务架构设计模式。'),
('微服务设计', 'Sam Newman', 79, '软件架构', '人民邮电出版社', '9787115400002', '纸质书', 'ok', '有货', 8, '/assets/microservices-design-2e-zh.jpg', '讲解微服务边界、部署与监控，适合微服务入门。');

-- BEGIN EXTRA BOOKS
-- 计算机 / 电子类扩充书目：由 scripts/book_import/fetch_books.py 生成，请勿手改。
-- 元数据经 Open Library 按 ISBN 核对；价格、库存与简介是课程演示数据。
INSERT IGNORE INTO books (title, author, price, category, publisher, isbn, format, stock_type, stock_text, stock_qty, cover_url, description) VALUES
('Structure and Interpretation of Computer Programs', 'Harold Abelson / Gerald Jay Sussman', 129, '程序设计基础', 'MIT Press', '9780262510875', '纸质书', 'ok', '有货', 18, '/assets/covers/9780262510875.jpg', '以 Scheme 语言讲解程序设计的核心抽象：过程与递归、数据抽象、模块化、状态与元语言，强调建立计算模型。'),
('Computer Systems: A Programmer''s Perspective', 'Randal E. Bryant / David R. O''Hallaron', 199, '计算机系统', 'Pearson', '9780134092669', '纸质书', 'ok', '有货', 22, '/assets/covers/9780134092669.jpg', '从程序员视角自底向上理解计算机系统：数据表示、汇编、处理器、存储层次、链接、异常控制流、虚拟内存与并发。'),
('The Art of Computer Programming, Volume 2', 'Donald E. Knuth', 299, '算法与数据结构', 'Addison-Wesley', '9780201896831', '纸质书', 'ok', '有货', 6, '/assets/covers/9780201896831.jpg', 'Knuth 经典巨著的第二卷，讨论随机数与伪随机序列、大整数算术、多项式运算等半数值算法的分析与实现。'),
('Code Complete', 'Steve McConnell', 128, '软件工程', 'Microsoft Press', '9780735619678', '纸质书', 'ok', '有货', 15, '/assets/covers/9780735619678.jpg', '从变量、控制结构、函数到调试与重构，系统整理可落地的编码实践与检查清单。'),
('Refactoring: Improving the Design of Existing Code', 'Martin Fowler', 139, '软件工程', 'Addison-Wesley', '9780134757599', '纸质书', 'ok', '有货', 12, '/assets/covers/9780134757599.jpg', '以实例驱动总结重构手法，讲清如何在保持外部行为不变的前提下改善代码设计。'),
('Design Patterns: Elements of Reusable Object-Oriented Software', 'Erich Gamma / Richard Helm / Ralph Johnson / John Vlissides', 119, '软件架构', 'Addison-Wesley', '9780201633610', '纸质书', 'ok', '有货', 20, '/assets/covers/9780201633610.jpg', 'GoF 的 23 个经典设计模式，逐一说明意图、结构、协作方式与适用场景。'),
('The Mythical Man-Month', 'Frederick P. Brooks', 79, '软件工程', 'Addison-Wesley', '9780201835953', '纸质书', 'ok', '有货', 25, '/assets/covers/9780201835953.jpg', '软件工程随笔经典，讨论人月神话、沟通成本、概念完整性与项目组织。'),
('Compilers: Principles, Techniques, and Tools', 'Alfred V. Aho / Monica S. Lam / Ravi Sethi / Jeffrey D. Ullman', 189, '编译原理', 'Addison-Wesley', '9780321486813', '纸质书', 'ok', '有货', 14, '/assets/covers/9780321486813.jpg', '编译原理经典教材（龙书），覆盖词法与语法分析、语义分析、中间表示、代码生成与优化。'),
('Modern Operating Systems', 'Andrew S. Tanenbaum / Herbert Bos', 179, '操作系统', 'Pearson', '9780133591620', '纸质书', 'ok', '有货', 16, '/assets/covers/9780133591620.jpg', '操作系统教材，讲解进程与线程、内存管理、文件系统、死锁与虚拟化。'),
('Operating System Concepts', 'Abraham Silberschatz / Peter B. Galvin / Greg Gagne', 169, '操作系统', 'Wiley', '9781118063330', '纸质书', 'ok', '有货', 10, '/assets/covers/9781118063330.jpg', '操作系统概念（恐龙书），覆盖进程同步、CPU 调度、内存管理与存储系统。'),
('Computer Networking: A Top-Down Approach', 'James F. Kurose / Keith W. Ross', 159, '计算机网络', 'Pearson', '9780132856201', '纸质书', 'ok', '有货', 21, '/assets/covers/9780132856201.jpg', '自顶向下讲解网络：应用层、传输层、网络层、链路层与无线网络。'),
('TCP/IP Illustrated, Volume 1', 'W. Richard Stevens', 149, '计算机网络', 'Addison-Wesley', '9780321336316', '纸质书', 'ok', '有货', 9, '/assets/covers/9780321336316.jpg', '结合协议报文与实现细节讲解 TCP/IP，卷一侧重协议栈与网络层、传输层行为。'),
('Database System Concepts', 'Abraham Silberschatz / Henry F. Korth / S. Sudarshan', 169, '数据库', 'McGraw-Hill', '9780073523323', '纸质书', 'ok', '有货', 13, '/assets/covers/9780073523323.jpg', '数据库系统原理教材：关系模型、SQL、事务、并发控制与故障恢复。'),
('High Performance MySQL', 'Baron Schwartz / Peter Zaitsev / Vadim Tkachenko', 119, '数据库', 'O''Reilly Media', '9781449314286', '纸质书', 'ok', '有货', 17, '/assets/covers/9781449314286.jpg', 'MySQL 性能实践：架构与索引、查询优化、复制、备份与高可用方案。'),
('Redis in Action', 'Josiah L. Carlson', 89, '数据库', 'Manning', '9781617290855', '纸质书', 'ok', '有货', 24, '/assets/covers/9781617290855.jpg', '用 Redis 构建应用：数据结构与命令、Lua 脚本、持久化、复制与集群。'),
('Effective Java', 'Joshua Bloch', 109, '编程语言', 'Addison-Wesley', '9780134685991', '纸质书', 'ok', '有货', 19, '/assets/covers/9780134685991.jpg', 'Java 编程实践指南，覆盖对象创建、泛型、枚举、并发与序列化等主题。'),
('Java Concurrency in Practice', 'Brian Goetz / Tim Peierls / Joshua Bloch', 99, '编程语言', 'Addison-Wesley', '9780321349606', '纸质书', 'ok', '有货', 11, '/assets/covers/9780321349606.jpg', '系统讲解 Java 并发：线程安全、锁与同步器、并发容器、任务执行与性能。'),
('Clean Code', 'Robert C. Martin', 89, '软件工程', 'Prentice Hall', '9780132350884', '纸质书', 'ok', '有货', 30, '/assets/covers/9780132350884.jpg', '代码整洁之道：命名、函数、注释、错误处理、单元测试与重构纪律。'),
('The Pragmatic Programmer', 'David Thomas / Andrew Hunt', 99, '软件工程', 'Addison-Wesley', '9780135957059', '纸质书', 'ok', '有货', 23, '/assets/covers/9780135957059.jpg', '程序员修炼之道：务实的方法论、工具使用、沟通与职业习惯。'),
('Domain-Driven Design', 'Eric Evans', 139, '软件架构', 'Addison-Wesley', '9780321125217', '纸质书', 'ok', '有货', 8, '/assets/covers/9780321125217.jpg', '领域驱动设计：通用语言、模型驱动设计、限界上下文与战略、战术设计。'),
('Patterns of Enterprise Application Architecture', 'Martin Fowler', 129, '软件架构', 'Addison-Wesley', '9780321127426', '纸质书', 'ok', '有货', 7, '/assets/covers/9780321127426.jpg', '企业应用架构模式目录：分层、领域逻辑、对象关系映射、并发与分布式。'),
('Site Reliability Engineering', 'Betsy Beyer / Chris Jones / Jennifer Petoff / Niall Richard Murphy', 119, '运维与可靠性', 'O''Reilly Media', '9781491929124', '纸质书', 'ok', '有货', 12, '/assets/covers/9781491929124.jpg', 'Google 站点可靠性工程实践：SLO 与错误预算、监控、发布、容量与事故响应。'),
('Designing Data-Intensive Applications', 'Martin Kleppmann', 139, '软件架构', 'O''Reilly Media', '9781449373320', '纸质书', 'ok', '有货', 26, '/assets/covers/9781449373320.jpg', '数据密集型应用系统设计：可靠性、可扩展性、存储引擎、复制、分区与流处理。'),
('Deep Learning', 'Ian Goodfellow / Yoshua Bengio / Aaron Courville', 269, '机器学习', 'MIT Press', '9780262035613', '纸质书', 'warn', '库存紧张', 5, '/assets/covers/9780262035613.jpg', '深度学习基础（花书）：线性代数、反向传播、正则化、卷积与循环网络、生成模型。'),
('Pattern Recognition and Machine Learning', 'Christopher M. Bishop', 259, '机器学习', 'Springer', '9780387310732', '纸质书', 'warn', '库存紧张', 4, '/assets/covers/9780387310732.jpg', '模式识别与机器学习：概率分布、回归与分类、核方法、图模型与近似推断。'),
('Artificial Intelligence: A Modern Approach', 'Stuart Russell / Peter Norvig', 239, '人工智能', 'Prentice Hall', '9780136042594', '纸质书', 'ok', '有货', 6, '/assets/covers/9780136042594.jpg', '人工智能经典教材：搜索、博弈、知识表示、概率推理、规划与机器学习。'),
('Computer Vision: Algorithms and Applications', 'Richard Szeliski', 199, '计算机视觉', 'Springer', '9781848829343', '纸质书', 'warn', '暂时缺货', 0, '/assets/covers/9781848829343.jpg', '计算机视觉：图像形成、特征检测、配准、分割、三维重建与识别。'),
('Digital Design and Computer Architecture', 'David Money Harris / Sarah L. Harris', 189, '数字电路', 'Morgan Kaufmann', '9780123944245', '纸质书', 'ok', '有货', 9, '/assets/covers/9780123944245.jpg', '从逻辑门、组合与时序电路讲到处理器微结构与存储层次。'),
('Microelectronic Circuits', 'Adel S. Sedra / Kenneth C. Smith', 219, '电子技术', 'Oxford University Press', '9780199339136', '纸质书', 'warn', '库存紧张', 4, '/assets/covers/9780199339136.jpg', '模拟与数字电子电路基础：器件模型、放大器、反馈、运算电路与频率响应。'),
('The C Programming Language', 'Brian W. Kernighan / Dennis M. Ritchie', 79, '编程语言', 'Prentice Hall', '9780131103627', '纸质书', 'ok', '有货', 28, '/assets/covers/9780131103627.jpg', 'C 语言经典教程（K&R），覆盖语法、指针、结构、输入输出与标准库。'),
('Reinforcement Learning: An Introduction', 'Richard S. Sutton / Andrew G. Barto', 199, '机器学习', 'MIT Press', '9780262039246', '纸质书', 'ok', '有货', 6, '/assets/covers/9780262039246.jpg', '强化学习导论：多臂老虎机、动态规划、蒙特卡洛、时序差分与函数逼近。'),
('The Go Programming Language', 'Alan A. A. Donovan / Brian W. Kernighan', 89, '编程语言', 'Addison-Wesley', '9780134190440', '纸质书', 'ok', '有货', 18, '/assets/covers/9780134190440.jpg', 'Go 语言实践指南：类型、接口、并发原语、测试与工程组织。'),
('Computer Architecture: A Quantitative Approach', 'John L. Hennessy / David A. Patterson', 249, '计算机体系结构', 'Morgan Kaufmann', '9780128119051', '纸质书', 'warn', '库存紧张', 5, '/assets/covers/9780128119051.jpg', '计算机体系结构：指令集、流水线、存储层次、并行与领域专用架构。'),
('The Elements of Statistical Learning', 'Trevor Hastie / Robert Tibshirani / Jerome Friedman', 229, '机器学习', 'Springer', '9780387848570', '纸质书', 'warn', '库存紧张', 3, '/assets/covers/9780387848570.jpg', '统计学习基础：监督学习、模型评估、正则化、树模型、集成与无监督方法。'),
('算法导论（原书第3版）', 'Thomas H. Cormen / Charles E. Leiserson / Ronald L. Rivest / Clifford Stein', 128, '算法', '机械工业出版社', '9787111407010', '纸质书', 'ok', '有货', 12, '/assets/covers/9787111407010.jpg', '系统讲解算法设计与分析的基础教材，覆盖排序、数据结构、图算法、动态规划与 NP 完全性。'),
('Java编程思想（第4版）', 'Bruce Eckel', 108, '编程语言', '机械工业出版社', '9787111213826', '纸质书', 'ok', '有货', 15, '/assets/covers/9787111213826.jpg', '从语言基础到泛型、并发与设计模式，结合大量示例讲解 Java 的编程思想。'),
('JavaScript高级程序设计（第3版）', 'Nicholas C. Zakas', 99, '编程语言', '人民邮电出版社', '9787115275790', '纸质书', 'ok', '有货', 14, '/assets/covers/9787115275790.jpg', '系统介绍 JavaScript 语言核心、DOM、事件、Ajax 与前端工程实践。'),
('Redis设计与实现', '黄健宏', 79, '数据库', '机械工业出版社', '9787111464747', '纸质书', 'ok', '有货', 18, '/assets/covers/9787111464747.jpg', '从源码层面剖析 Redis 的数据结构、持久化、复制、哨兵与集群实现。'),
('数据库系统概念（原书第6版）', 'Abraham Silberschatz / Henry F. Korth / S. Sudarshan', 99, '数据库', '机械工业出版社', '9787111375296', '纸质书', 'ok', '有货', 10, '/assets/covers/9787111375296.jpg', '数据库领域的经典教材，覆盖关系模型、SQL、事务、并发控制与恢复。'),
('C程序设计语言（第2版·新版）', 'Brian W. Kernighan / Dennis M. Ritchie', 45, '编程语言', '机械工业出版社', '9787111128069', '纸质书', 'ok', '有货', 20, '/assets/covers/9787111128069.jpg', 'C 语言创始人撰写的经典教程，以简洁示例讲解指针、结构体与标准库。'),
('深入理解计算机系统（原书第3版）', 'Randal E. Bryant / David R. O''Hallaron', 139, '计算机系统', '机械工业出版社', '9787111544937', '纸质书', 'ok', '有货', 9, '/assets/covers/9787111544937.jpg', '从程序员视角讲解数据表示、汇编、处理器、存储层次、链接、虚拟内存与并发。'),
('计算机组成原理（第2版）', '唐朔飞', 45, '计算机体系结构', '高等教育出版社', '9787040223903', '纸质书', 'ok', '有货', 16, '/assets/covers/9787040223903.jpg', '高校计算机组成原理教材，讲解运算器、存储器、控制器、总线与输入输出系统。'),
('数据结构（C语言版）', '严蔚敏 / 吴伟民', 39, '算法与数据结构', '清华大学出版社', '9787302147510', '纸质书', 'ok', '有货', 22, '/assets/covers/9787302147510.jpg', '以 C 语言描述线性表、树、图、查找与排序等经典数据结构与算法。'),
('计算机操作系统（第4版）', '汤小丹 / 梁红兵 / 哲凤屏 / 汤子瀛', 45, '操作系统', '西安电子科技大学出版社', '9787560633503', '纸质书', 'ok', '有货', 17, '/assets/covers/9787560633503.jpg', '操作系统课程教材，覆盖进程管理、内存管理、文件系统与设备管理。'),
('概率论与数理统计（第4版）', '盛骤 / 谢式千 / 潘承毅', 39, '数学 / 概率', '高等教育出版社', '9787040238969', '纸质书', 'ok', '有货', 19, '/assets/covers/9787040238969.jpg', '理工科概率论与数理统计教材，包含随机变量、参数估计与假设检验。'),
('线性代数（第6版）', '同济大学数学系', 34, '数学 / 概率', '高等教育出版社', '9787040396614', '纸质书', 'ok', '有货', 21, '/assets/covers/9787040396614.jpg', '工科线性代数教材，讲解行列式、矩阵、向量组、特征值与二次型。');
-- END EXTRA BOOKS
