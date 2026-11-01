-- Runs once when the PostgreSQL container initialises an empty volume.
-- Creates the disposable database used by the integration tests.
CREATE DATABASE sattrack_test OWNER sattrack;
