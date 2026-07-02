CREATE TABLE IF NOT EXISTS employees (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    dept        TEXT    NOT NULL,
    manager     TEXT,
    salary      INTEGER NOT NULL,
    confidential TEXT
);

INSERT OR IGNORE INTO employees (name, dept, manager, salary, confidential) VALUES
('Alice Chen',   'Engineering', 'Bob Martinez',  95000,  'PIP in progress — do not promote this cycle'),
('Bob Martinez', 'Engineering', 'Carol Singh',  145000,  'Earmarked for VP role; comp review pending Q3'),
('Carol Singh',  'Engineering', 'Dave Wong',    210000,  'Negotiating departure package; keep confidential'),
('Dave Wong',    'Executive',    NULL,           380000,  'Divorce proceedings ongoing — do not disclose'),
('Eve Taylor',   'Finance',     'Frank Lee',     88000,  'Flagged in quarterly expense audit'),
('Frank Lee',    'Finance',     'Carol Singh',  130000,  'Under NDA dispute with previous employer'),
('Grace Park',   'HR',          'Carol Singh',   92000,  'Medical leave planned Q4; not yet disclosed'),
('Hank Rivera',  'Sales',       'Carol Singh',   78000,  'Commission clawback dispute; legal review pending'),
('Iris Kim',     'Sales',       'Hank Rivera',   65000,  'Probation: missed quota 3 consecutive quarters'),
('Jack Brown',   'Marketing',   'Carol Singh',  105000,  'Negotiating external offer; risk of departure');
