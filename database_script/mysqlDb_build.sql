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

CREATE TABLE `portfolio` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `description` varchar(500) NULL,
  `active` tinyint NOT NULL DEFAULT '1',
  `date_added` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `id_UNIQUE` (`id`)
);

CREATE TABLE `portfolio_securities` (
  `id` int NOT NULL AUTO_INCREMENT,
  `portfolio_id` int NOT NULL,
  `ticker_id` int NOT NULL,
  `date_added` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `portfolio_ticker_unique` (`portfolio_id`, `ticker_id`),
  CONSTRAINT `portfolio_securities_ibfk_1` FOREIGN KEY (`portfolio_id`) REFERENCES `portfolio` (`id`),
  CONSTRAINT `portfolio_securities_ibfk_2` FOREIGN KEY (`ticker_id`) REFERENCES `tickers` (`id`)
);

CREATE TABLE `portfolio_transactions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `portfolio_id` int NOT NULL,
  `security_id` int NOT NULL,
  `transaction_type` enum('buy','sell','dividend') NOT NULL,
  `transaction_date` date NOT NULL,
  `shares` int DEFAULT NULL,
  `price` decimal(10,2) DEFAULT NULL,
  `amount` decimal(10,2) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `portfolio_id` (`portfolio_id`),
  KEY `security_id` (`security_id`),
  CONSTRAINT `portfolio_transactions_ibfk_1` FOREIGN KEY (`portfolio_id`) REFERENCES `portfolio` (`id`),
  CONSTRAINT `portfolio_transactions_ibfk_2` FOREIGN KEY (`security_id`) REFERENCES `portfolio_securities` (`id`)
);

CREATE TABLE `portfolio_value` (
  `id` int NOT NULL AUTO_INCREMENT,
  `portfolio_id` int NOT NULL,
  `calculation_date` date NOT NULL,
  `value` decimal(18,2) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `portfolio_id` (`portfolio_id`),
  CONSTRAINT `portfolio_value_ibfk_1` FOREIGN KEY (`portfolio_id`) REFERENCES `portfolio` (`id`)
);

CREATE TABLE `price_direction` (
  `id` int NOT NULL AUTO_INCREMENT,
  `ticker_id` int NOT NULL,
  `direction` varchar(10) NOT NULL,
  `date_added` date NOT NULL,
  PRIMARY KEY (`id`),
  KEY `id_ticker_id` (`ticker_id`)
);

INSERT INTO `__EFMigrationsHistory` (`MigrationId`, `ProductVersion`)
VALUES ('20230310232623_InitialCreate', '6.0.10');

COMMIT;
