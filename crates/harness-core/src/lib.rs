//! Repository Harness V1 pure core.
//!
//! The crate deliberately contains no SQLite, V0 reader, task lifecycle, target-tool
//! runner, scheduler, or operational database. Phase 3 adds an
//! explicitly injected, authenticated filesystem mutation/recovery boundary.

pub mod application;
pub mod command_spec;
pub mod domain;
pub mod infrastructure;
pub mod interface;
pub mod markdown;
pub mod path;
pub mod ports;
pub mod recovery;
mod strict_json;
pub mod trust;
mod unicode_casefold;
