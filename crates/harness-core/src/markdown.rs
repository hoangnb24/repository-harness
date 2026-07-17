//! Deterministic, non-executing CommonMark structural parsing.

use std::collections::{BTreeMap, BTreeSet};

use pulldown_cmark::{Event, Parser, Tag, TagEnd};
use unicode_normalization::UnicodeNormalization;

#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct MarkdownDocument {
    pub links: Vec<String>,
    pub anchors: BTreeSet<String>,
}

pub fn parse_commonmark(text: &str) -> MarkdownDocument {
    let mut links = Vec::new();
    let mut heading = None::<String>;
    let mut heading_texts = Vec::new();

    for event in Parser::new(text) {
        match event {
            Event::Start(Tag::Link { dest_url, .. } | Tag::Image { dest_url, .. }) => {
                links.push(dest_url.into_string());
            }
            Event::Start(Tag::Heading { .. }) => heading = Some(String::new()),
            Event::End(TagEnd::Heading(_)) => {
                if let Some(text) = heading.take() {
                    heading_texts.push(text);
                }
            }
            Event::Text(text) | Event::Code(text) if heading.is_some() => {
                heading
                    .as_mut()
                    .expect("heading is present")
                    .push_str(&text);
            }
            Event::SoftBreak | Event::HardBreak if heading.is_some() => {
                heading.as_mut().expect("heading is present").push(' ');
            }
            _ => {}
        }
    }

    let mut counts = BTreeMap::<String, usize>::new();
    let mut anchors = BTreeSet::new();
    for heading in heading_texts {
        let base = github_anchor(&heading);
        if base.is_empty() {
            continue;
        }
        let count = counts.entry(base.clone()).or_default();
        let anchor = if *count == 0 {
            base
        } else {
            format!("{base}-{count}")
        };
        *count += 1;
        anchors.insert(anchor);
    }

    MarkdownDocument { links, anchors }
}

fn github_anchor(value: &str) -> String {
    let normalized: String = value.nfc().collect();
    let mut slug = String::new();
    for character in normalized.chars().flat_map(char::to_lowercase) {
        if character.is_alphanumeric() || character == '_' || character == '-' {
            slug.push(character);
        } else if character.is_whitespace() {
            slug.push('-');
        }
    }
    slug
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_commonmark_link_forms_and_ignores_code_or_malformed_text() {
        let markdown = r#"
[ref]: docs/reference.md "Reference title"
[collapsed]: docs/collapsed.md
[shortcut]: docs/shortcut.md

[inline](docs/a\(b\).md "Title") ![image](images/a.png 'Image')
[full][ref] [collapsed][] [shortcut]
`[code](do-not-read.md)`

    [indented-code](do-not-read-either.md)

[malformed](docs/no-close.md
[bad-title](bad.md"not separated")
"#;
        let parsed = parse_commonmark(markdown);
        assert_eq!(
            parsed.links,
            [
                "docs/a(b).md",
                "images/a.png",
                "docs/reference.md",
                "docs/collapsed.md",
                "docs/shortcut.md",
            ]
        );
    }

    #[test]
    fn parses_multiline_commonmark_links_and_headings() {
        let parsed = parse_commonmark(
            "[multiline](\n  docs/multiline.md\n  \"title\"\n)\n\nHeading *with* `Code`\n---\n",
        );
        assert_eq!(parsed.links, ["docs/multiline.md"]);
        assert!(parsed.anchors.contains("heading-with-code"));
    }

    #[test]
    fn headings_cover_atx_setext_fences_and_duplicate_suffixes() {
        let parsed = parse_commonmark(
            "# Hello *World*\n## Hello World\nSetext `Code`\n---\n```\n# ignored\n```\n",
        );
        assert!(parsed.anchors.contains("hello-world"));
        assert!(parsed.anchors.contains("hello-world-1"));
        assert!(parsed.anchors.contains("setext-code"));
        assert!(!parsed.anchors.contains("ignored"));

        let unicode = parse_commonmark("# Straße\n");
        assert!(unicode.anchors.contains("straße"));
        assert!(!unicode.anchors.contains("strasse"));

        let literal_hyphens = parse_commonmark("# build--test\n# -edge-\n");
        assert!(literal_hyphens.anchors.contains("build--test"));
        assert!(literal_hyphens.anchors.contains("-edge-"));
    }
}
