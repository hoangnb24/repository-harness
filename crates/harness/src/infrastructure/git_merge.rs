use std::fs;
use std::process::Command;

use crate::application::{PortError, ThreeWayMergePort};
use crate::domain::MergeOutcome;

#[derive(Clone, Copy, Default)]
pub struct GitThreeWayMerge;

impl ThreeWayMergePort for GitThreeWayMerge {
    fn available(&self) -> Result<bool, PortError> {
        Ok(Command::new("git")
            .arg("--version")
            .output()
            .map(|output| output.status.success())
            .unwrap_or(false))
    }

    fn merge(&self, base: &[u8], local: &[u8], upstream: &[u8]) -> Result<MergeOutcome, PortError> {
        let temp = tempfile::tempdir().map_err(io_error)?;
        let local_path = temp.path().join("local");
        let base_path = temp.path().join("base");
        let upstream_path = temp.path().join("upstream");
        fs::write(&local_path, local).map_err(io_error)?;
        fs::write(&base_path, base).map_err(io_error)?;
        fs::write(&upstream_path, upstream).map_err(io_error)?;
        let output = Command::new("git")
            .args([
                "merge-file",
                "-p",
                "--diff3",
                "-L",
                "LOCAL",
                "-L",
                "BASE",
                "-L",
                "UPSTREAM",
            ])
            .arg(&local_path)
            .arg(&base_path)
            .arg(&upstream_path)
            .output()
            .map_err(|error| PortError::new(format!("could not run git merge-file: {error}")))?;
        match output.status.code() {
            Some(0) => Ok(MergeOutcome::Clean(output.stdout)),
            Some(1) => Ok(MergeOutcome::Conflict {
                content: output.stdout,
                detail: "local and upstream changes overlap".to_owned(),
            }),
            _ => Err(PortError::new(format!(
                "git merge-file failed: {}",
                String::from_utf8_lossy(&output.stderr).trim()
            ))),
        }
    }
}

fn io_error(error: std::io::Error) -> PortError {
    PortError::new(error.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn git_merges_non_overlapping_changes_and_reports_overlap() {
        let merger = GitThreeWayMerge;
        let clean = merger
            .merge(
                b"one\ntwo\nthree\n",
                b"ONE\ntwo\nthree\n",
                b"one\ntwo\nTHREE\n",
            )
            .unwrap();
        assert!(matches!(clean, MergeOutcome::Clean(_)));
        let conflict = merger.merge(b"one\n", b"local\n", b"upstream\n").unwrap();
        assert!(matches!(conflict, MergeOutcome::Conflict { .. }));
    }
}
