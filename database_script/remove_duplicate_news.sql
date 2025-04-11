DELETE FROM investing.news_sentiment
WHERE id in (
	select id from (
		SELECT id, headline,
				row_number() over (PARTITION by headline order by headline) as intRow
		FROM investing.news_sentiment
	) dup_news 
	where intRow > 1
);
