//! Repository Harness V1 pure core.
//!
//! The crate deliberately contains no SQLite, V0 reader, task lifecycle, target-tool
//! runner, scheduler, or mutation executor. Phase 2 parses, authenticates, inspects,
//! plans, previews, and refuses writes that require Phase 3 recovery guarantees.

pub mod application;
pub mod command_spec;
pub mod domain;
pub mod infrastructure;
pub mod interface;
pub mod markdown;
pub mod path;
pub mod ports;
mod strict_json;
pub mod trust;
mod unicode_casefold;
