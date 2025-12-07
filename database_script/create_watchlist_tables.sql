-- Create the watch list tables

CREATE TABLE IF NOT EXISTS `watch_lists` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `description` varchar(500) NULL,
  `date_created` datetime DEFAULT CURRENT_TIMESTAMP,
  `user_id` int DEFAULT NULL, -- For future multi-user support
  PRIMARY KEY (`id`),
  UNIQUE KEY `name_user_unique` (`name`, `user_id`)
);

CREATE TABLE IF NOT EXISTS `watch_list_tickers` (
  `id` int NOT NULL AUTO_INCREMENT,
  `watch_list_id` int NOT NULL,
  `ticker_id` int NOT NULL,
  `date_added` datetime DEFAULT CURRENT_TIMESTAMP,
  `notes` varchar(500) NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `watchlist_ticker_unique` (`watch_list_id`, `ticker_id`),
  CONSTRAINT `watch_list_tickers_ibfk_1` FOREIGN KEY (`watch_list_id`) REFERENCES `watch_lists` (`id`) ON DELETE CASCADE,
  CONSTRAINT `watch_list_tickers_ibfk_2` FOREIGN KEY (`ticker_id`) REFERENCES `tickers` (`id`) ON DELETE CASCADE
);