use std::collections::BTreeMap;
use std::path::Path;

use rusqlite::{types::ValueRef, Connection, OpenFlags};
use serde::{Deserialize, Serialize};

use crate::capture::{hex_sha256, source_digest, Capture};
use crate::Result;

pub const EXPORT_SCHEMA: &str = "repository-harness-v0-export/v1";

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub struct NeutralExport {
    pub schema: String,
    pub source: ExportSource,
    pub categories: Vec<ExportCategory>,
    pub records: Vec<ExportTable>,
    pub unknown_unowned: Vec<String>,
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct ExportSource {
    pub schema_version: u32,
    pub source_sha256: String,
    pub standalone_backup_sha256: String,
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct ExportCategory {
    pub source_id: String,
    pub category: String,
    pub payload_sha256: String,
    pub disposition: String,
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub struct ExportTable {
    pub source_id: String,
    pub category: String,
    pub disposition: String,
    pub rows: Vec<BTreeMap<String, NeutralValue>>,
    pub payload_sha256: String,
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(tag = "type", content = "value", rename_all = "lowercase")]
pub enum NeutralValue {
    Null,
    Integer(i64),
    RealBits(String),
    Text(String),
    TextBytesHex(String),
    BlobHex(String),
}

pub fn build(capture: &Capture) -> Result<(NeutralExport, Vec<u8>, String)> {
    let temporary = tempfile::Builder::new()
        .prefix("harness-v0-export-")
        .tempdir()?;
    let snapshot = temporary.path().join("standalone.db");
    std::fs::write(&snapshot, &capture.standalone_backup)?;
    let connection = Connection::open_with_flags(&snapshot, OpenFlags::SQLITE_OPEN_READ_ONLY)?;
    connection.pragma_update(None, "query_only", true)?;
    let records = export_tables(&connection)?;
    let categories = capture
        .members
        .iter()
        .map(|member| ExportCategory {
            source_id: member.path.clone(),
            category: member.category.clone(),
            payload_sha256: member.sha256.clone(),
            disposition: "bridge-only-legacy".into(),
        })
        .collect();
    let export = NeutralExport {
        schema: EXPORT_SCHEMA.into(),
        source: ExportSource {
            schema_version: capture.schema_version,
            source_sha256: source_digest(capture),
            standalone_backup_sha256: capture.standalone_backup_sha256.clone(),
        },
        categories,
        records,
        unknown_unowned: capture.unknown_metadata.clone(),
    };
    let mut bytes = serde_json::to_vec(&export)?;
    bytes.push(b'\n');
    let digest = hex_sha256(&bytes);
    Ok((export, bytes, digest))
}

fn export_tables(connection: &Connection) -> Result<Vec<ExportTable>> {
    let mut names = connection
        .prepare(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name",
        )?
        .query_map([], |row| row.get::<_, String>(0))?
        .collect::<std::result::Result<Vec<_>, _>>()?;
    names.sort();
    let mut tables = Vec::new();
    for name in names {
        let sql = format!("SELECT * FROM {}", quote_identifier(&name));
        let mut statement = connection.prepare(&sql)?;
        let columns = statement
            .column_names()
            .into_iter()
            .map(str::to_owned)
            .collect::<Vec<_>>();
        let mut encoded_rows = Vec::new();
        let mut rows = statement.query([])?;
        while let Some(row) = rows.next()? {
            let mut values = BTreeMap::new();
            for (index, column) in columns.iter().enumerate() {
                let value = match row.get_ref(index)? {
                    ValueRef::Null => NeutralValue::Null,
                    ValueRef::Integer(value) => NeutralValue::Integer(value),
                    ValueRef::Real(value) => {
                        NeutralValue::RealBits(format!("{:016x}", value.to_bits()))
                    }
                    ValueRef::Text(value) => match std::str::from_utf8(value) {
                        Ok(value) => NeutralValue::Text(value.to_owned()),
                        Err(_) => NeutralValue::TextBytesHex(hex_bytes(value)),
                    },
                    ValueRef::Blob(value) => NeutralValue::BlobHex(hex_bytes(value)),
                };
                values.insert(column.clone(), value);
            }
            let encoded = serde_json::to_vec(&values)?;
            encoded_rows.push((encoded, values));
        }
        encoded_rows.sort_by(|left, right| left.0.cmp(&right.0));
        let rows = encoded_rows
            .into_iter()
            .map(|(_, values)| values)
            .collect::<Vec<_>>();
        let payload = serde_json::to_vec(&rows)?;
        tables.push(ExportTable {
            source_id: format!("sqlite.table.{name}"),
            category: format!("sqlite.table.{name}"),
            disposition: "bridge-only-legacy".into(),
            rows,
            payload_sha256: hex_sha256(&payload),
        });
    }
    Ok(tables)
}

fn quote_identifier(value: &str) -> String {
    format!("\"{}\"", value.replace('"', "\"\""))
}

fn hex_bytes(value: &[u8]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut output = String::with_capacity(value.len() * 2);
    for byte in value {
        output.push(HEX[(byte >> 4) as usize] as char);
        output.push(HEX[(byte & 0x0f) as usize] as char);
    }
    output
}

#[allow(dead_code)]
pub fn load(path: &Path) -> Result<NeutralExport> {
    Ok(serde_json::from_slice(&std::fs::read(path)?)?)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn neutral_values_preserve_text_bytes_nul_extremes_real_bits_and_blobs() {
        let connection = Connection::open_in_memory().unwrap();
        connection
            .execute_batch(
                "CREATE TABLE exact_values(value);\n\
                 INSERT INTO exact_values VALUES(NULL);\n\
                 INSERT INTO exact_values VALUES(-9223372036854775808);\n\
                 INSERT INTO exact_values VALUES(9223372036854775807);\n\
                 INSERT INTO exact_values VALUES(CAST(X'80ff' AS TEXT));\n\
                 INSERT INTO exact_values VALUES(CAST(X'610062' AS TEXT));\n\
                 INSERT INTO exact_values VALUES(CAST(X'7ff8000000000001' AS BLOB));\n\
                 INSERT INTO exact_values VALUES(X'00ff10');",
            )
            .unwrap();
        connection
            .execute(
                "INSERT INTO exact_values VALUES(?1)",
                [f64::from_bits(0x8000_0000_0000_0000)],
            )
            .unwrap();
        connection
            .execute(
                "INSERT INTO exact_values VALUES(?1)",
                [f64::from_bits(0x3ff1_9999_9999_999a)],
            )
            .unwrap();
        connection
            .execute(
                "INSERT INTO exact_values VALUES(?1)",
                [f64::from_bits(0x7ff0_0000_0000_0000)],
            )
            .unwrap();
        let tables = export_tables(&connection).unwrap();
        let rows = &tables[0].rows;
        assert!(rows.iter().any(|row| row["value"] == NeutralValue::Null));
        assert!(rows
            .iter()
            .any(|row| row["value"] == NeutralValue::Integer(i64::MIN)));
        assert!(rows
            .iter()
            .any(|row| row["value"] == NeutralValue::Integer(i64::MAX)));
        assert!(rows.iter().any(|row| matches!(
            &row["value"],
            NeutralValue::Text(value) if value.as_bytes() == b"a\0b"
        )));
        assert!(rows.iter().any(|row| matches!(
            &row["value"],
            NeutralValue::RealBits(value) if value == "8000000000000000"
        )));
        assert!(rows.iter().any(|row| matches!(
            &row["value"],
            NeutralValue::RealBits(value) if value == "3ff199999999999a"
        )));
        assert!(rows.iter().any(|row| matches!(
            &row["value"],
            NeutralValue::RealBits(value) if value == "7ff0000000000000"
        )));
        assert!(rows.iter().any(|row| matches!(
            &row["value"],
            NeutralValue::BlobHex(value) if value == "00ff10"
        )));
        assert!(rows.iter().any(|row| matches!(
            &row["value"],
            NeutralValue::TextBytesHex(value) if value == "80ff"
        )));
    }
}
