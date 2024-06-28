CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100)
);

CREATE TABLE trainers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100)
);

CREATE TABLE user_trainer_mapping (
    user_id INTEGER,
    trainer_id INTEGER,
    PRIMARY KEY (user_id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (trainer_id) REFERENCES trainers(id)
);