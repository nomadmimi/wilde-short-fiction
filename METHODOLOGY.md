<!--
DRAFT. This file is rendered on wildeshortfiction.com/about and travels with every
Zenodo release, so it is the one place the methodology is described.
Lines marked "TO CONFIRM" contain wording inferred from the data; check and edit them,
then delete the markers (and this comment) before the release.
-->

## Scope

The dataset collects reviews, notices and related press items about Oscar Wilde's three short story collections: *The Happy Prince and Other Tales* (1888), *Lord Arthur Savile's Crime and Other Stories* (1891) and *A House of Pomegranates* (1891). An item is in scope when it discusses at least one of these collections and was printed in a periodical. Each record is classified by `publication_type`:

- **Contemporary review (original)**: a review first printed in the periodical named.
- **Contemporary review (reprint)**: a review reprinted from another periodical (the original source is given in `comments` where known).
- **News**: a news item that mentions a collection without reviewing it.
- **Advertisement**: a publisher's or bookseller's advertisement for a collection.

The `period` field groups items chronologically: period 1 covers the first reception of the collections (1888–1894); period 3 covers items from 1895, the year of Wilde's trials. (TO CONFIRM: definition of each period, and what period 2 will hold.)

## Finding the reviews

Reviews were located by searching digitised newspaper and periodical collections, mainly the British Newspaper Archive, HathiTrust Digital Library, Newspapers.com by Ancestry, Google Books and NewspaperArchive, with smaller numbers from Chronicling America, the Irish Newspaper Archives, Welsh Newspapers Online, the Internet Archive and the British Library. The archive used is recorded for every item in `archive_name`, with a stable link in `archive_url` and the date it was consulted in `accessed`. (TO CONFIRM: search terms used, and whether existing bibliographies such as Mason (1914) and Mikhail (1978) were checked for leads.)

## Transcription

Every review is transcribed by hand from the digitised page; none of the text is uncorrected OCR. Transcriptions follow these conventions:

- Original spelling, punctuation and typographical errors are kept. Errors in the original are marked `[sic]`.
- Editorial additions are placed in square brackets.
- Titles and other text italicised in the original are marked with asterisks (`*A House of Pomegranates*`).
- Long dashes are rendered as `---`.
- Omitted passages are marked with an ellipsis (`...`). (TO CONFIRM: whether ellipses are always editorial or sometimes in the original.)

The date each transcription was completed is recorded in `transcribed`.

## Metadata

Each record gives the periodical's name, country, region and place of publication; the volume, number and page(s); the date of publication to the precision known (year, month, day); and the reviewer where identified. Most Victorian reviews were unsigned, so `publication_reviewer` is usually empty.

## Limitations

The dataset depends on what has been digitised and what is searchable. Provincial, colonial and non-English-language periodicals are under-represented, and the absence of a periodical does not mean it did not review the collections. Corrections and additions are welcome through the website's Contribute page.
