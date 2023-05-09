CREATE TABLE IF NOT EXISTS `__EFMigrationsHistory` (
    `MigrationId` varchar(150) NOT NULL,
    `ProductVersion` varchar(32) NOT NULL,
    CONSTRAINT `PK___EFMigrationsHistory` PRIMARY KEY (`MigrationId`)
);

START TRANSACTION;

CREATE TABLE `activity` (
    `id` int NOT NULL AUTO_INCREMENT,
    `ticker_id` int NOT NULL,
    `activity_date` date NOT NULL,
    `open` decimal(9,4) NOT NULL,
    `close` decimal(9,4) NOT NULL,
    `volume` int NOT NULL,
    `updown` varchar(10) NULL,
    `high` decimal(9,4) NULL,
    `low` decimal(9,4) NULL,
    CONSTRAINT `PK_activity` PRIMARY KEY (`id`)
);

CREATE TABLE `averages` (
    `id` int NOT NULL AUTO_INCREMENT,
    `ticker_id` int NOT NULL,
    `activity_date` date NOT NULL,
    `value` decimal(9,2) NULL,
    `average_type` varchar(50) NULL,
    CONSTRAINT `PK_averages` PRIMARY KEY (`id`)
);

CREATE TABLE `tickers` (
    `id` int NOT NULL AUTO_INCREMENT,
    `ticker` varchar(10) NULL,
    `ticker_name` varchar(45) NULL,
    `trend` varchar(25) NULL,
    `close` float NULL,
    `industry` varchar(100) NULL,
    `sector` varchar(100) NULL,
    CONSTRAINT `PK_tickers` PRIMARY KEY (`id`)
);

CREATE TABLE `rsi` (
    `id` int NOT NULL AUTO_INCREMENT,
    `ticker_id` int NOT NULL,
    `avg_loss` decimal(9,2) NOT NULL,
    `avg_gain` decimal(9,2) NOT NULL,
    `rs` decimal(9,2) NOT NULL,
    `rsi` decimal(9,2) NOT NULL,
    CONSTRAINT `PK_rsi` PRIMARY KEY (`id`),
    CONSTRAINT `id` FOREIGN KEY (`ticker_id`) REFERENCES `tickers` (`id`)
);

CREATE INDEX `id_idx` ON `rsi` (`ticker_id`);

INSERT INTO `__EFMigrationsHistory` (`MigrationId`, `ProductVersion`)
VALUES ('20230310232623_InitialCreate', '6.0.10');

COMMIT;

