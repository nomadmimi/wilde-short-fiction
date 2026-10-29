## Scope

The dataset collects reviews, notices and related press items about Oscar Wilde's three short story collections: *The Happy Prince and Other Tales* (1888), *Lord Arthur Savile's Crime and Other Stories* (1891) and *A House of Pomegranates* (1891). An item is in scope when it discusses at least one of these collections and was printed in a periodical. Each record is classified by `publication_type`:

- **Contemporary review**: a review of one or more of the collections.
- **Notice**: a short notice of a collection, shorter than a review.
- **News**: a news item that mentions a collection without reviewing it.
- **Article**: an article that discusses a collection without being a review of it.
- **Correspondence**: a letter to the editor that discusses a collection.
- **Obituary**: an obituary of Wilde that discusses a collection.
- **Advertisement**: a publisher's or bookseller's advertisement for a collection.

The `period` field groups items chronologically: period 1 covers the first reception of the collections (to 31 March 1895); period 2 runs from Wilde's trials (April 1895) to 30 November 1900; period 3 covers items after Wilde's death.

## Reprints and chains

The same review was often reprinted in several periodicals. Each printing is a separate record, and `publication_type` marks a review as an original or a reprint. Records that are not independent of each other share a `chain_id`: `W` for the same text printed in several periodicals (verbatim or with small variants, or sharing a substantial passage), `L` for letters that answer one another, `Q` for a text that quotes another record. Records in no chain have an empty `chain_id`. When counting, a chain counts once, so a widely reprinted text does not weigh more than a review printed once.

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

Each record gives the periodical's name, country, region and place of publication; the volume, number and page(s); the date of publication to the precision known (year, month, day); and the reviewer where identified. Most Victorian reviews were unsigned, so `publication_reviewer` is usually empty. Every record has a `citekey` for reference managers.

## Publication

The dataset is compiled in a working spreadsheet that holds more records than are published here. A record is published once it has been checked: records found before the website was first built, and later records whose page images have been checked during analysis. Each record is cleared for publication individually. `data.csv` is generated from the spreadsheet by a script and never edited by hand; every export arrives as a pull request whose log lists any record left out and why, and is published only when that pull request is merged. Every published record is also an item in the "Reception reviews" collection of the project's [public Zotero group](https://www.zotero.org/groups/6738308), linked to its page on the website.

## Responsibilities

Regina M. Ponciano is responsible for the dataset: finding, transcribing and checking the records, and deciding which are published. Claude, an AI model by Anthropic, is responsible for its translation to this repository and the website: the export from the spreadsheet, the checks in `datapackage.json`, the scripts and the automated workflows. Every change Claude makes is reviewed and merged by Regina M. Ponciano.

## Limitations

The dataset depends on what has been digitised and what is searchable. Provincial, colonial and non-English-language periodicals are under-represented, and the absence of a periodical does not mean it did not review the collections. Corrections and additions are welcome through the website's Contribute page.
