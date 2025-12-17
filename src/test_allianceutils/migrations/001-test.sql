-- This is a comment to make sure comments don't break it
DROP TABLE IF EXISTS test_run_sql_from_file;
/*! alternate style comment */
CREATE TABLE test_run_sql_from_file (id int, value varchar(15));

-- This is another comment to make sure comments don't break it
INSERT INTO test_run_sql_from_file (id, value) VALUES (1, 'entry one');

INSERT INTO test_run_sql_from_file (id, value) VALUES (2, 'entry two');
