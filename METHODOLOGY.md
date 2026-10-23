## Scope

The dataset collects reviews, notices and related press items about Oscar Wilde's three short story collections: *The Happy Prince and Other Tales* (1888), *Lord Arthur Savile's Crime and Other Stories* (1891) and *A House of Pomegranates* (1891). An item is in scope when it discusses at least one of these collections and was printed in a periodical. Each record is classified by `publication_type`:

- **Contemporary review**: a review of one or more of the collections.
- **News**: a news item that mentions a collection without reviewing it.
- **Advertisement**: a publisher's or bookseller's advertisement for a collection.

The same review was often reprinted in several periodicals. The dataset does not yet distinguish original reviews from reprints: each printing is a separate record. Linking reprints of the same text into clusters with shared identifiers is planned for a future release.

The `period` field groups items chronologically: period 1 covers the first reception of the collections (1888–1894); period 3 covers items from 1895, the year of Wilde's trials.

## Finding the reviews

Reviews were located by searching digitised newspaper and periodical collections, mainly the British Newspaper Archive, HathiTrust Digital Library, Newspapers.com by Ancestry, Google Books and NewspaperArchive, with smaller numbers from Chronicling America, the Irish Newspaper Archives, Welsh Newspapers Online, the Internet Archive and the British Library. The archive used is recorded for every item in `archive_name`, with a stable link in `archive_url` and the date it was consulted in `accessed`.

## Transcription

Transcriptions are checked against the digitised page, but some OCR errors may remain. Corrections are ongoing, and every change to a transcription is recorded in the [history of `data.csv`](https://github.com/nomadmimi/wilde-short-fiction/commits/main/data.csv), where any correction can be checked against the previous version. When quoting a transcription, please verify it against the source linked in `archive_url`. Transcriptions follow these conventions:

- Original spelling, punctuation and typographical errors are kept, and errors in the original are marked `[sic]`.
- Editorial additions are placed in square brackets.
- Titles and other text italicised in the original are marked with asterisks (`*A House of Pomegranates*`).
- Long dashes are rendered as `---`.
- Omitted passages are marked with an ellipsis (`...`).

The date each transcription was completed is recorded in `transcribed`.

## Metadata

Each record gives the periodical's name, country, region and place of publication; the volume, number and page(s); the date of publication to the precision known (year, month, day); and the reviewer where identified. Most Victorian reviews were unsigned, so `publication_reviewer` is usually empty.

## Limitations

The dataset depends on what has been digitised and what is searchable. Provincial, colonial and non-English-language periodicals are under-represented, and the absence of a periodical does not mean it did not review the collections. Corrections and additions are welcome through the website's Contribute page.
