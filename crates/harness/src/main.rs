use std::io::{self, Write};

use clap::Parser;
use harness::application::{CoreApplication, InspectionApplication, SelfUpdateApplication};
use harness::infrastructure::{
    ClaudeSessionLog, EmbeddedCoreDistribution, FileSystemInstallationState, GitThreeWayMerge,
    LatestReleaseCandidates,
};
use harness::interface::{execute, Cli};

fn main() {
    let cli = Cli::parse();
    let application = CoreApplication::new(
        EmbeddedCoreDistribution,
        FileSystemInstallationState,
        GitThreeWayMerge,
    );
    let self_update = SelfUpdateApplication::new(
        LatestReleaseCandidates::default(),
        FileSystemInstallationState,
    );
    let inspection = InspectionApplication::new(ClaudeSessionLog);
    let exit = execute(cli, &application, &self_update, &inspection);
    if !exit.stdout.is_empty() {
        let _ = io::stdout().write_all(exit.stdout.as_bytes());
    }
    if !exit.stderr.is_empty() {
        let _ = io::stderr().write_all(exit.stderr.as_bytes());
    }
    std::process::exit(exit.code);
}
