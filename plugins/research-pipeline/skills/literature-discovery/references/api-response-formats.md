# API Response Formats

Parsing guides for each academic search API.

## OpenAlex

### Works Search Response

```json
{
  "results": [
    {
      "id": "https://openalex.org/W1234567890",
      "doi": "https://doi.org/10.1234/example",
      "title": "Paper Title",
      "publication_year": 2024,
      "authorships": [
        {
          "author": {
            "id": "https://openalex.org/A1234",
            "display_name": "Jane Smith"
          },
          "institutions": [{ "display_name": "MIT" }]
        }
      ],
      "primary_location": {
        "source": {
          "display_name": "Nature Communications"
        }
      },
      "abstract_inverted_index": {
        "This": [0],
        "paper": [1],
        "examines": [2]
      },
      "cited_by_count": 42,
      "concepts": [
        { "display_name": "Machine Learning", "score": 0.95 }
      ]
    }
  ],
  "meta": {
    "count": 1234,
    "per_page": 50,
    "page": 1
  }
}
```

### Reconstructing Abstract from Inverted Index

OpenAlex stores abstracts as inverted indexes. To reconstruct:

```
1. Collect all entries: { word: [positions] }
2. Create an array of length = max(all positions) + 1
3. For each word, place it at each position
4. Join array with spaces
```

Example:
```
Input: { "This": [0], "paper": [1, 5], "examines": [2], "how": [3], "the": [4] }
Output: "This paper examines how the paper"
```

### Extracting DOI

OpenAlex DOIs include the full URL prefix. Strip it:
```
"https://doi.org/10.1234/example" → "10.1234/example"
```

## Semantic Scholar

### Paper Search Response

```json
{
  "total": 500,
  "offset": 0,
  "data": [
    {
      "paperId": "abc123def456",
      "title": "Paper Title",
      "abstract": "Full abstract text here...",
      "year": 2024,
      "authors": [
        { "authorId": "12345", "name": "Jane Smith" }
      ],
      "externalIds": {
        "DOI": "10.1234/example",
        "ArXiv": "2401.12345",
        "CorpusId": 12345678
      },
      "citationCount": 42,
      "referenceCount": 35
    }
  ]
}
```

### References / Citations Response

Same structure as search but nested under `citedPaper` or `citingPaper`:

```json
{
  "data": [
    {
      "citedPaper": {
        "paperId": "...",
        "title": "...",
        "abstract": "...",
        "year": 2023,
        "authors": [...],
        "externalIds": { "DOI": "...", "ArXiv": "..." }
      }
    }
  ]
}
```

## arXiv

### Search Response (Atom XML)

```xml
<feed xmlns="http://www.w3.org/2005/Atom">
  <totalResults>1234</totalResults>
  <entry>
    <id>http://arxiv.org/abs/2401.12345v1</id>
    <title>Paper Title</title>
    <summary>Abstract text here...</summary>
    <author><name>Jane Smith</name></author>
    <author><name>John Doe</name></author>
    <published>2024-01-15T00:00:00Z</published>
    <link href="http://arxiv.org/abs/2401.12345v1" rel="alternate" type="text/html"/>
    <link href="http://arxiv.org/pdf/2401.12345v1" rel="related" type="application/pdf"/>
    <arxiv:primary_category term="cs.CR" />
  </entry>
</feed>
```

### Extracting arXiv ID

From the `<id>` element:
```
"http://arxiv.org/abs/2401.12345v1" → "2401.12345"
```

Strip the version suffix (v1, v2, etc.) for deduplication purposes.

## CrossRef (for DOI verification)

### Works by DOI Response

```json
{
  "status": "ok",
  "message": {
    "DOI": "10.1234/example",
    "title": ["Paper Title"],
    "author": [
      { "given": "Jane", "family": "Smith" }
    ],
    "published-print": { "date-parts": [[2024, 3, 15]] },
    "container-title": ["Nature Communications"],
    "abstract": "<p>Abstract text with HTML tags...</p>"
  }
}
```

Note: CrossRef abstracts may contain HTML tags. Strip them before comparison.

### Title Matching

For fuzzy title matching between stored citation and API response:
1. Lowercase both titles
2. Remove punctuation and extra whitespace
3. Remove common prefixes ("a ", "the ", "an ")
4. Compare using character-level similarity (Levenshtein ratio)
5. Threshold: >0.85 = match, 0.70-0.85 = probable match, <0.70 = mismatch

## DataCite (for DOI verification — dataset DOIs)

### DOI Response

```json
{
  "data": {
    "id": "10.1234/example",
    "type": "dois",
    "attributes": {
      "doi": "10.1234/example",
      "titles": [{ "title": "Dataset Title" }],
      "creators": [{ "name": "Smith, Jane" }],
      "publicationYear": 2024,
      "descriptions": [{ "description": "Abstract...", "descriptionType": "Abstract" }]
    }
  }
}
```
