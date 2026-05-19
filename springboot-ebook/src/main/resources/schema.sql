DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS cart_items;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS books;

CREATE TABLE users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(60) NOT NULL UNIQUE,
    password VARCHAR(128) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    signature VARCHAR(200),
    level VARCHAR(30) NOT NULL
);

CREATE TABLE books (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(150) NOT NULL,
    author VARCHAR(100) NOT NULL,
    price INT NOT NULL,
    category VARCHAR(120) NOT NULL,
    publisher VARCHAR(120) NOT NULL,
    isbn VARCHAR(30) NOT NULL UNIQUE,
    format VARCHAR(60) NOT NULL,
    stock_type VARCHAR(50) NOT NULL,
    stock_text VARCHAR(50) NOT NULL,
    description TEXT NOT NULL
);

CREATE TABLE cart_items (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    book_id BIGINT NOT NULL,
    qty INT NOT NULL,
    selected BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE KEY uk_cart_user_book (user_id, book_id),
    CONSTRAINT fk_cart_user FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT fk_cart_book FOREIGN KEY (book_id) REFERENCES books(id)
);

CREATE TABLE orders (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_no VARCHAR(40) NOT NULL UNIQUE,
    user_id BIGINT NOT NULL,
    book_id BIGINT NOT NULL,
    qty INT NOT NULL,
    unit_price INT NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_order_user FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT fk_order_book FOREIGN KEY (book_id) REFERENCES books(id)
);
