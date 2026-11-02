//! Read-only inspection: skill receipt compliance and token use.

use std::path::{Path, PathBuf};

use crate::application::PortError;
use crate::domain::{build_skill_report, SessionEvent, SkillReport};

#[derive(Debug, Clone, Default)]
pub struct ParsedSession {
    pub events: Vec<SessionEvent>,
    pub malformed_lines: u64,
    pub sidechain_records: u64,
}

#[derive(Debug, thiserror::Error)]
pub enum SessionLogError {
    #[error("{path}: unsupported session format; only Claude Code JSONL sessions are supported")]
    Unsupported { path: String },
    #[error(transparent)]
    Port(#[from] PortError),
}

pub trait SessionLogPort {
    fn read_session(&self, path: &Path) -> Result<ParsedSession, SessionLogError>;
}

#[derive(Debug, thiserror::Error)]
pub enum InspectionError {
    /// Wrong invocation, such as an unsupported session format.
    #[error("{0}")]
    Usage(String),
    #[error(transparent)]
    Port(#[from] PortError),
}

#[derive(Debug, Clone)]
pub struct SessionSkillReport {
    pub sessions: Vec<String>,
    pub report: SkillReport,
    pub malformed_lines: u64,
    pub sidechain_records: u64,
}

pub struct InspectionApplication<L> {
    sessions: L,
}

impl<L: SessionLogPort> InspectionApplication<L> {
    pub fn new(sessions: L) -> Self {
        Self { sessions }
    }

    pub fn skill_report(&self, paths: &[PathBuf]) -> Result<SessionSkillReport, InspectionError> {
        let mut events = Vec::new();
        let mut malformed_lines = 0;
        let mut sidechain_records = 0;
        for path in paths {
            let parsed = self
                .sessions
                .read_session(path)
                .map_err(|error| match error {
                    SessionLogError::Unsupported { .. } => {
                        InspectionError::Usage(error.to_string())
                    }
                    SessionLogError::Port(error) => InspectionError::Port(error),
                })?;
            // Each session starts a fresh turn.
            events.push(SessionEvent::Prompt);
            events.extend(parsed.events);
            malformed_lines += parsed.malformed_lines;
            sidechain_records += parsed.sidechain_records;
        }
        Ok(SessionSkillReport {
            sessions: paths
                .iter()
                .map(|path| path.display().to_string())
                .collect(),
            report: build_skill_report(events),
            malformed_lines,
            sidechain_records,
        })
    }
}
