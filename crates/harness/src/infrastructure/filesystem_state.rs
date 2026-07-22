use std::fs::{self, File, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

use fs2::FileExt;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use crate::application::{InstallationStatePort, PortError};
use crate::domain::{
    ApplyReceipt, BaselineFile, ContentHash, FrozenWorkspaceFile, InstallationState, RelativePath,
    ResolutionConflict, UpdateResolutionSession, WorkspaceMutation,
};

#[derive(Clone, Copy, Default)]
pub struct FileSystemInstallationState;

impl InstallationStatePort for FileSystemInstallationState {
    fn recover_interrupted(&self, root: &Path) -> Result<bool, PortError> {
        ensure_workspace_root(root)?;
        let state_root = state_root(root);
        if !state_root.exists() {
            return Ok(false);
        }
        reject_symlink(&state_root, ".harness-core")?;
        fs::create_dir_all(&state_root).map_err(io_error)?;
        ensure_state_ignore(&state_root)?;
        let lock = acquire_lock(&state_root)?;
        let result = recover_locked(root, &state_root);
        FileExt::unlock(&lock).map_err(io_error)?;
        result
    }

    fn transaction_pending(&self, root: &Path) -> Result<bool, PortError> {
        Ok(state_root(root).join("transaction.json").exists())
    }

    fn load(&self, root: &Path) -> Result<Option<InstallationState>, PortError> {
        if !root.exists() {
            return Ok(None);
        }
        validate_workspace_root(root)?;
        load_state(root)
    }

    fn read_workspace_file(
        &self,
        root: &Path,
        path: &RelativePath,
    ) -> Result<Option<Vec<u8>>, PortError> {
        if !root.exists() {
            return Ok(None);
        }
        self.validate_managed_path(root, path)?;
        let target = root.join(path.as_str());
        if !target.exists() {
            return Ok(None);
        }
        let metadata = fs::symlink_metadata(&target).map_err(io_error)?;
        if !metadata.is_file() {
            return Err(PortError::new(format!(
                "managed path is not a regular file: {path}"
            )));
        }
        fs::read(target).map(Some).map_err(io_error)
    }

    fn validate_managed_path(&self, root: &Path, path: &RelativePath) -> Result<(), PortError> {
        if !root.exists() {
            return Ok(());
        }
        validate_workspace_root(root)?;
        let mut current = root.to_path_buf();
        for component in path.as_str().split('/') {
            current.push(component);
            if current.exists() {
                reject_symlink(&current, path.as_str())?;
            }
        }
        Ok(())
    }

    fn apply(
        &self,
        root: &Path,
        state: &InstallationState,
        mutations: &[WorkspaceMutation],
    ) -> Result<ApplyReceipt, PortError> {
        ensure_workspace_root(root)?;
        state
            .validate()
            .map_err(|error| PortError::new(error.to_string()))?;
        let state_root = state_root(root);
        if state_root.exists() {
            reject_symlink(&state_root, ".harness-core")?;
        }
        fs::create_dir_all(&state_root).map_err(io_error)?;
        ensure_state_ignore(&state_root)?;
        let lock = acquire_lock(&state_root)?;
        recover_locked(root, &state_root)?;
        let result = apply_locked(root, &state_root, state, mutations);
        let result = match result {
            Ok(receipt) => Ok(receipt),
            Err(error) => match recover_locked(root, &state_root) {
                Ok(_) => Err(error),
                Err(recovery_error) => Err(PortError::new(format!(
                    "{error}; automatic recovery also failed: {recovery_error}"
                ))),
            },
        };
        FileExt::unlock(&lock).map_err(io_error)?;
        result
    }

    fn apply_if_unchanged(
        &self,
        root: &Path,
        state: &InstallationState,
        mutations: &[WorkspaceMutation],
        expected: &[FrozenWorkspaceFile],
    ) -> Result<ApplyReceipt, PortError> {
        ensure_workspace_root(root)?;
        state
            .validate()
            .map_err(|error| PortError::new(error.to_string()))?;
        let state_root = state_root(root);
        if state_root.exists() {
            reject_symlink(&state_root, ".harness-core")?;
        }
        fs::create_dir_all(&state_root).map_err(io_error)?;
        ensure_state_ignore(&state_root)?;
        let lock = acquire_lock(&state_root)?;
        recover_locked(root, &state_root)?;
        let result = verify_frozen_locked(root, expected)
            .and_then(|_| apply_locked(root, &state_root, state, mutations));
        let result = match result {
            Ok(receipt) => Ok(receipt),
            Err(error) => match recover_locked(root, &state_root) {
                Ok(_) => Err(error),
                Err(recovery_error) => Err(PortError::new(format!(
                    "{error}; automatic recovery also failed: {recovery_error}"
                ))),
            },
        };
        FileExt::unlock(&lock).map_err(io_error)?;
        result
    }

    fn resolution_pending(&self, root: &Path) -> Result<bool, PortError> {
        if !root.exists() {
            return Ok(false);
        }
        validate_workspace_root(root)?;
        let state_root = state_root(root);
        if !state_root.exists() {
            return Ok(false);
        }
        reject_symlink(&state_root, ".harness-core")?;
        Ok(update_root(&state_root).join("session.json").is_file())
    }

    fn stage_resolution(
        &self,
        root: &Path,
        session: &UpdateResolutionSession,
    ) -> Result<(), PortError> {
        ensure_workspace_root(root)?;
        let state_root = state_root(root);
        if state_root.exists() {
            reject_symlink(&state_root, ".harness-core")?;
        }
        fs::create_dir_all(&state_root).map_err(io_error)?;
        ensure_state_ignore(&state_root)?;
        let lock = acquire_lock(&state_root)?;
        let result = stage_resolution_locked(&state_root, session);
        FileExt::unlock(&lock).map_err(io_error)?;
        result
    }

    fn load_resolution(&self, root: &Path) -> Result<Option<UpdateResolutionSession>, PortError> {
        if !root.exists() {
            return Ok(None);
        }
        validate_workspace_root(root)?;
        let state_root = state_root(root);
        if !state_root.exists() {
            return Ok(None);
        }
        reject_symlink(&state_root, ".harness-core")?;
        load_resolution_session(&state_root)
    }

    fn clear_resolution(&self, root: &Path) -> Result<bool, PortError> {
        if !root.exists() {
            return Ok(false);
        }
        validate_workspace_root(root)?;
        let state_root = state_root(root);
        if !state_root.exists() {
            return Ok(false);
        }
        reject_symlink(&state_root, ".harness-core")?;
        let lock = acquire_lock(&state_root)?;
        let path = update_root(&state_root);
        let removed = path.exists();
        if removed {
            reject_symlink(&path, ".harness-core/update")?;
        }
        let result = remove_dir_if_exists(&path).map(|_| removed);
        FileExt::unlock(&lock).map_err(io_error)?;
        result
    }
}

fn stage_resolution_locked(
    state_root: &Path,
    session: &UpdateResolutionSession,
) -> Result<(), PortError> {
    if session.conflicts.is_empty() {
        return Err(PortError::new("cannot stage an empty resolution session"));
    }
    let update_root = update_root(state_root);
    if update_root.exists() {
        reject_symlink(&update_root, ".harness-core/update")?;
    }
    remove_dir_if_exists(&update_root)?;
    fs::create_dir_all(&update_root).map_err(io_error)?;
    let mut conflicts = Vec::new();
    for conflict in &session.conflicts {
        validate_resolution_path(&update_root, &conflict.path)?;
        for (directory, content) in [
            ("base", &conflict.base),
            ("local", &conflict.local),
            ("incoming", &conflict.incoming),
            ("resolved", &conflict.resolved),
        ] {
            copy_bytes(
                content,
                &update_root.join(directory).join(conflict.path.as_str()),
            )?;
        }
        conflicts.push(ResolutionConflictDto {
            path: conflict.path.as_str().to_owned(),
        });
    }
    let mut frozen_files = Vec::new();
    for frozen in &session.frozen_files {
        validate_resolution_path(&update_root, &frozen.path)?;
        if let Some(content) = &frozen.content {
            copy_bytes(
                content,
                &update_root.join("frozen").join(frozen.path.as_str()),
            )?;
        }
        frozen_files.push(FrozenWorkspaceFileDto {
            path: frozen.path.as_str().to_owned(),
            present: frozen.content.is_some(),
        });
    }
    let dto = ResolutionSessionDto {
        schema_version: 2,
        from_version: session.from_version.clone(),
        to_version: session.to_version.clone(),
        conflicts,
        frozen_files,
    };
    write_json_atomic(&update_root.join("session.json"), &dto, "resolution")
}

fn load_resolution_session(
    state_root: &Path,
) -> Result<Option<UpdateResolutionSession>, PortError> {
    let update_root = update_root(state_root);
    let session_path = update_root.join("session.json");
    if !session_path.exists() {
        return Ok(None);
    }
    reject_symlink(&update_root, ".harness-core/update")?;
    reject_symlink(&session_path, ".harness-core/update/session.json")?;
    let dto: ResolutionSessionDto = read_json(&session_path)?;
    if dto.schema_version != 2 {
        return Err(PortError::new(format!(
            "unsupported update resolution schema: {}",
            dto.schema_version
        )));
    }
    let mut conflicts = Vec::new();
    for item in dto.conflicts {
        let path =
            RelativePath::parse(item.path).map_err(|error| PortError::new(error.to_string()))?;
        validate_resolution_path(&update_root, &path)?;
        conflicts.push(ResolutionConflict {
            base: read_resolution_file(&update_root, "base", &path)?,
            local: read_resolution_file(&update_root, "local", &path)?,
            incoming: read_resolution_file(&update_root, "incoming", &path)?,
            resolved: read_resolution_file(&update_root, "resolved", &path)?,
            path,
        });
    }
    let mut frozen_files = Vec::new();
    for item in dto.frozen_files {
        let path =
            RelativePath::parse(item.path).map_err(|error| PortError::new(error.to_string()))?;
        validate_resolution_path(&update_root, &path)?;
        let content = if item.present {
            Some(read_resolution_file(&update_root, "frozen", &path)?)
        } else {
            let target = update_root.join("frozen").join(path.as_str());
            if target.exists() {
                return Err(PortError::new(format!(
                    "absent frozen path unexpectedly exists: {path}"
                )));
            }
            None
        };
        frozen_files.push(FrozenWorkspaceFile { path, content });
    }
    Ok(Some(UpdateResolutionSession {
        from_version: dto.from_version,
        to_version: dto.to_version,
        conflicts,
        frozen_files,
    }))
}

fn read_resolution_file(
    update_root: &Path,
    directory: &str,
    path: &RelativePath,
) -> Result<Vec<u8>, PortError> {
    let target = update_root.join(directory).join(path.as_str());
    validate_resolution_path(update_root, path)?;
    let metadata = fs::symlink_metadata(&target).map_err(|error| {
        PortError::new(format!(
            "could not read {directory} resolution for {path}: {error}"
        ))
    })?;
    if !metadata.is_file() || metadata.file_type().is_symlink() {
        return Err(PortError::new(format!(
            "resolution input is not a regular file: {}",
            target.display()
        )));
    }
    fs::read(target).map_err(io_error)
}

fn validate_resolution_path(update_root: &Path, path: &RelativePath) -> Result<(), PortError> {
    for directory in ["base", "local", "incoming", "resolved", "frozen"] {
        let mut current = update_root.join(directory);
        if current.exists() {
            reject_symlink(&current, directory)?;
        }
        for component in path.as_str().split('/') {
            current.push(component);
            if current.exists() {
                reject_symlink(&current, path.as_str())?;
            }
        }
    }
    Ok(())
}

fn ensure_state_ignore(state_root: &Path) -> Result<(), PortError> {
    let path = state_root.join(".gitignore");
    let rules = [
        "/lock",
        "/transaction.json",
        "/base.next-*",
        "/update/",
        "/update-candidate/",
    ];
    if path.exists() {
        reject_symlink(&path, ".harness-core/.gitignore")?;
        let metadata = fs::metadata(&path).map_err(io_error)?;
        if !metadata.is_file() {
            return Err(PortError::new(
                ".harness-core/.gitignore is not a regular file",
            ));
        }
        let mut content = fs::read_to_string(&path).map_err(io_error)?;
        let mut changed = false;
        for rule in rules {
            if !content.lines().any(|line| line.trim() == rule) {
                if !content.is_empty() && !content.ends_with('\n') {
                    content.push('\n');
                }
                content.push_str(rule);
                content.push('\n');
                changed = true;
            }
        }
        if changed {
            copy_bytes_atomic(content.as_bytes(), &path, "ignore")?;
        }
        return Ok(());
    }
    copy_bytes(
        b"/lock\n/transaction.json\n/base.next-*\n/update/\n/update-candidate/\n",
        &path,
    )
}

fn verify_frozen_locked(root: &Path, expected: &[FrozenWorkspaceFile]) -> Result<(), PortError> {
    for frozen in expected {
        validate_path(root, &frozen.path)?;
        let target = root.join(frozen.path.as_str());
        let actual = if target.exists() {
            let metadata = fs::symlink_metadata(&target).map_err(io_error)?;
            if !metadata.is_file() || metadata.file_type().is_symlink() {
                return Err(PortError::new(format!(
                    "workspace changed after conflict detection for {}",
                    frozen.path
                )));
            }
            Some(fs::read(target).map_err(io_error)?)
        } else {
            None
        };
        if actual != frozen.content {
            return Err(PortError::new(format!(
                "workspace changed after conflict detection for {}",
                frozen.path
            )));
        }
    }
    Ok(())
}

fn apply_locked(
    root: &Path,
    state_root: &Path,
    state: &InstallationState,
    mutations: &[WorkspaceMutation],
) -> Result<ApplyReceipt, PortError> {
    let id = transaction_id()?;
    let backup_relative = format!(".harness-backup/harness-core-{id}");
    let backup_root = root.join(&backup_relative);
    let state_existed =
        state_root.join("manifest.json").exists() || state_root.join("base").exists();
    let mut records = Vec::new();

    for mutation in mutations {
        let path = mutation.path();
        validate_path(root, path)?;
        let target = root.join(path.as_str());
        let existed = target.exists();
        if existed {
            let metadata = fs::symlink_metadata(&target).map_err(io_error)?;
            if !metadata.is_file() {
                return Err(PortError::new(format!(
                    "cannot back up non-file managed path: {path}"
                )));
            }
            let backup = backup_root.join("files").join(path.as_str());
            copy_file(&target, &backup)?;
        }
        records.push(JournalFile {
            path: path.as_str().to_owned(),
            existed,
        });
    }

    if state_existed {
        let state_backup = backup_root.join("state");
        fs::create_dir_all(&state_backup).map_err(io_error)?;
        let manifest = state_root.join("manifest.json");
        if manifest.exists() {
            copy_file(&manifest, &state_backup.join("manifest.json"))?;
        }
        let base = state_root.join("base");
        if base.exists() {
            copy_tree(&base, &state_backup.join("base"))?;
        }
    }

    let mut journal = TransactionJournal {
        schema_version: 1,
        id: id.clone(),
        phase: TransactionPhase::Applying,
        backup_relative: backup_relative.clone(),
        state_existed,
        files: records,
    };
    write_json_atomic(&state_root.join("transaction.json"), &journal, &id)?;

    for mutation in mutations {
        match mutation {
            WorkspaceMutation::Write { path, content } => {
                write_workspace_atomic(root, path, content, &id)?;
            }
            WorkspaceMutation::Delete { path } => {
                let target = root.join(path.as_str());
                if target.exists() {
                    fs::remove_file(target).map_err(io_error)?;
                }
            }
        }
    }

    write_state(state_root, state, &id)?;
    journal.phase = TransactionPhase::Committed;
    write_json_atomic(&state_root.join("transaction.json"), &journal, &id)?;
    fs::remove_file(state_root.join("transaction.json")).map_err(io_error)?;

    let backup_has_content = state_existed
        || mutations.iter().any(|mutation| {
            backup_root
                .join("files")
                .join(mutation.path().as_str())
                .exists()
        });
    if !backup_has_content && backup_root.exists() {
        fs::remove_dir_all(&backup_root).map_err(io_error)?;
    }
    Ok(ApplyReceipt {
        backup_path: backup_has_content.then_some(backup_relative),
    })
}

fn recover_locked(root: &Path, state_root: &Path) -> Result<bool, PortError> {
    let journal_path = state_root.join("transaction.json");
    if !journal_path.exists() {
        return Ok(false);
    }
    let journal: TransactionJournal = read_json(&journal_path)?;
    if journal.schema_version != 1 {
        return Err(PortError::new(format!(
            "unsupported transaction journal schema: {}",
            journal.schema_version
        )));
    }
    if journal.phase == TransactionPhase::Committed {
        fs::remove_file(journal_path).map_err(io_error)?;
        return Ok(true);
    }

    let backup_root = root.join(&journal.backup_relative);
    for record in &journal.files {
        let path = RelativePath::parse(record.path.clone())
            .map_err(|error| PortError::new(error.to_string()))?;
        validate_path(root, &path)?;
        let target = root.join(path.as_str());
        if record.existed {
            let backup = backup_root.join("files").join(path.as_str());
            if !backup.is_file() {
                return Err(PortError::new(format!(
                    "transaction backup is missing: {}",
                    backup.display()
                )));
            }
            copy_file_atomic(&backup, &target, &journal.id)?;
        } else if target.exists() {
            fs::remove_file(target).map_err(io_error)?;
        }
    }

    let manifest = state_root.join("manifest.json");
    let base = state_root.join("base");
    remove_if_exists(&manifest)?;
    remove_dir_if_exists(&base)?;
    if journal.state_existed {
        let state_backup = backup_root.join("state");
        if state_backup.join("manifest.json").exists() {
            copy_file_atomic(&state_backup.join("manifest.json"), &manifest, &journal.id)?;
        }
        if state_backup.join("base").exists() {
            copy_tree(&state_backup.join("base"), &base)?;
        }
    }
    remove_dir_if_exists(&state_root.join(format!("base.next-{}", journal.id)))?;
    fs::remove_file(journal_path).map_err(io_error)?;
    Ok(true)
}

fn load_state(root: &Path) -> Result<Option<InstallationState>, PortError> {
    let state_root = state_root(root);
    if !state_root.exists() {
        return Ok(None);
    }
    reject_symlink(&state_root, ".harness-core")?;
    let manifest_path = state_root.join("manifest.json");
    if !manifest_path.exists() {
        return Ok(None);
    }
    let manifest: ManifestDto = read_json(&manifest_path)?;
    let mut files = Vec::new();
    for file in manifest.files {
        let path =
            RelativePath::parse(file.path).map_err(|error| PortError::new(error.to_string()))?;
        let expected = ContentHash::parse(file.upstream_sha256)
            .map_err(|error| PortError::new(error.to_string()))?;
        let base_path = state_root.join("base").join(path.as_str());
        validate_state_base_path(&state_root, &base_path)?;
        let content = fs::read(&base_path).map_err(|error| {
            PortError::new(format!("could not read base {}: {error}", path.as_str()))
        })?;
        let actual = hash_bytes(&content)?;
        if actual != expected {
            return Err(PortError::new(format!(
                "base hash mismatch for {}: expected {}, got {}",
                path,
                expected.as_str(),
                actual.as_str()
            )));
        }
        files.push(BaselineFile {
            path,
            content,
            hash: expected,
        });
    }
    let state = InstallationState {
        schema_version: manifest.schema_version,
        core_version: manifest.core_version,
        files,
    };
    state
        .validate()
        .map_err(|error| PortError::new(error.to_string()))?;
    Ok(Some(state))
}

fn write_state(state_root: &Path, state: &InstallationState, id: &str) -> Result<(), PortError> {
    let next_base = state_root.join(format!("base.next-{id}"));
    remove_dir_if_exists(&next_base)?;
    fs::create_dir_all(&next_base).map_err(io_error)?;
    let mut files = Vec::new();
    for baseline in &state.files {
        let actual = hash_bytes(&baseline.content)?;
        if actual != baseline.hash {
            return Err(PortError::new(format!(
                "provided baseline hash differs for {}",
                baseline.path
            )));
        }
        let target = next_base.join(baseline.path.as_str());
        copy_bytes(&baseline.content, &target)?;
        files.push(ManifestFileDto {
            path: baseline.path.as_str().to_owned(),
            upstream_sha256: baseline.hash.as_str().to_owned(),
        });
    }
    let manifest = ManifestDto {
        schema_version: state.schema_version,
        core_version: state.core_version.clone(),
        files,
    };
    let base = state_root.join("base");
    remove_dir_if_exists(&base)?;
    fs::rename(&next_base, &base).map_err(io_error)?;
    write_json_atomic(&state_root.join("manifest.json"), &manifest, id)
}

fn validate_path(root: &Path, path: &RelativePath) -> Result<(), PortError> {
    let mut current = root.to_path_buf();
    for component in path.as_str().split('/') {
        current.push(component);
        if current.exists() {
            reject_symlink(&current, path.as_str())?;
        }
    }
    Ok(())
}

fn validate_state_base_path(state_root: &Path, target: &Path) -> Result<(), PortError> {
    let relative = target
        .strip_prefix(state_root)
        .map_err(|_| PortError::new("base path escaped state root"))?;
    let mut current = state_root.to_path_buf();
    for component in relative.components() {
        current.push(component);
        if current.exists() {
            reject_symlink(&current, &target.display().to_string())?;
        }
    }
    Ok(())
}

fn write_workspace_atomic(
    root: &Path,
    path: &RelativePath,
    content: &[u8],
    id: &str,
) -> Result<(), PortError> {
    validate_path(root, path)?;
    let target = root.join(path.as_str());
    copy_bytes_atomic(content, &target, id)
}

fn copy_file_atomic(source: &Path, target: &Path, id: &str) -> Result<(), PortError> {
    let bytes = fs::read(source).map_err(io_error)?;
    copy_bytes_atomic(&bytes, target, id)
}

fn copy_bytes_atomic(content: &[u8], target: &Path, id: &str) -> Result<(), PortError> {
    let parent = target
        .parent()
        .ok_or_else(|| PortError::new(format!("target has no parent: {}", target.display())))?;
    fs::create_dir_all(parent).map_err(io_error)?;
    let name = target
        .file_name()
        .and_then(|value| value.to_str())
        .ok_or_else(|| PortError::new(format!("invalid target filename: {}", target.display())))?;
    let temp = parent.join(format!(".{name}.harness-{id}.tmp"));
    copy_bytes(content, &temp)?;
    fs::rename(&temp, target).map_err(io_error)
}

fn copy_bytes(content: &[u8], target: &Path) -> Result<(), PortError> {
    if let Some(parent) = target.parent() {
        fs::create_dir_all(parent).map_err(io_error)?;
    }
    let mut file = File::create(target).map_err(io_error)?;
    file.write_all(content).map_err(io_error)?;
    file.sync_all().map_err(io_error)
}

fn copy_file(source: &Path, target: &Path) -> Result<(), PortError> {
    let bytes = fs::read(source).map_err(io_error)?;
    copy_bytes(&bytes, target)
}

fn copy_tree(source: &Path, target: &Path) -> Result<(), PortError> {
    fs::create_dir_all(target).map_err(io_error)?;
    for entry in fs::read_dir(source).map_err(io_error)? {
        let entry = entry.map_err(io_error)?;
        let source_path = entry.path();
        let target_path = target.join(entry.file_name());
        let metadata = fs::symlink_metadata(&source_path).map_err(io_error)?;
        if metadata.file_type().is_symlink() {
            return Err(PortError::new(format!(
                "refusing symlink in state tree: {}",
                source_path.display()
            )));
        }
        if metadata.is_dir() {
            copy_tree(&source_path, &target_path)?;
        } else if metadata.is_file() {
            copy_file(&source_path, &target_path)?;
        }
    }
    Ok(())
}

fn write_json_atomic<T: Serialize>(target: &Path, value: &T, id: &str) -> Result<(), PortError> {
    let bytes = serde_json::to_vec_pretty(value)
        .map_err(|error| PortError::new(format!("could not encode JSON: {error}")))?;
    copy_bytes_atomic(&bytes, target, id)
}

fn read_json<T: for<'de> Deserialize<'de>>(path: &Path) -> Result<T, PortError> {
    let bytes = fs::read(path).map_err(io_error)?;
    serde_json::from_slice(&bytes)
        .map_err(|error| PortError::new(format!("could not parse {}: {error}", path.display())))
}

fn acquire_lock(state_root: &Path) -> Result<File, PortError> {
    let lock = OpenOptions::new()
        .create(true)
        .read(true)
        .write(true)
        .truncate(false)
        .open(state_root.join("lock"))
        .map_err(io_error)?;
    FileExt::lock_exclusive(&lock).map_err(io_error)?;
    Ok(lock)
}

fn ensure_workspace_root(root: &Path) -> Result<(), PortError> {
    if !root.exists() {
        fs::create_dir_all(root).map_err(io_error)?;
    }
    validate_workspace_root(root)
}

fn validate_workspace_root(root: &Path) -> Result<(), PortError> {
    let metadata = fs::metadata(root).map_err(io_error)?;
    if !metadata.is_dir() {
        return Err(PortError::new(format!(
            "workspace root is not a directory: {}",
            root.display()
        )));
    }
    Ok(())
}

fn reject_symlink(path: &Path, label: &str) -> Result<(), PortError> {
    let metadata = fs::symlink_metadata(path).map_err(io_error)?;
    if metadata.file_type().is_symlink() {
        return Err(PortError::new(format!(
            "refusing symlink for managed path {label}: {}",
            path.display()
        )));
    }
    Ok(())
}

fn remove_if_exists(path: &Path) -> Result<(), PortError> {
    if path.exists() {
        fs::remove_file(path).map_err(io_error)?;
    }
    Ok(())
}

fn remove_dir_if_exists(path: &Path) -> Result<(), PortError> {
    if path.exists() {
        fs::remove_dir_all(path).map_err(io_error)?;
    }
    Ok(())
}

fn state_root(root: &Path) -> PathBuf {
    root.join(".harness-core")
}

fn update_root(state_root: &Path) -> PathBuf {
    state_root.join("update")
}

fn transaction_id() -> Result<String, PortError> {
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|error| PortError::new(error.to_string()))?
        .as_nanos();
    Ok(format!("{nanos}-{}", std::process::id()))
}

fn hash_bytes(content: &[u8]) -> Result<ContentHash, PortError> {
    ContentHash::parse(format!("{:x}", Sha256::digest(content)))
        .map_err(|error| PortError::new(error.to_string()))
}

fn io_error(error: std::io::Error) -> PortError {
    PortError::new(error.to_string())
}

#[derive(Debug, Deserialize, Serialize)]
struct ManifestDto {
    schema_version: u32,
    core_version: String,
    files: Vec<ManifestFileDto>,
}

#[derive(Debug, Deserialize, Serialize)]
struct ManifestFileDto {
    path: String,
    upstream_sha256: String,
}

#[derive(Debug, Deserialize, Serialize)]
struct TransactionJournal {
    schema_version: u32,
    id: String,
    phase: TransactionPhase,
    backup_relative: String,
    state_existed: bool,
    files: Vec<JournalFile>,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
enum TransactionPhase {
    Applying,
    Committed,
}

#[derive(Debug, Deserialize, Serialize)]
struct JournalFile {
    path: String,
    existed: bool,
}

#[derive(Debug, Deserialize, Serialize)]
struct ResolutionSessionDto {
    schema_version: u32,
    from_version: String,
    to_version: String,
    conflicts: Vec<ResolutionConflictDto>,
    frozen_files: Vec<FrozenWorkspaceFileDto>,
}

#[derive(Debug, Deserialize, Serialize)]
struct ResolutionConflictDto {
    path: String,
}

#[derive(Debug, Deserialize, Serialize)]
struct FrozenWorkspaceFileDto {
    path: String,
    present: bool,
}

#[cfg(test)]
mod tests {
    use super::*;

    fn state(content: &[u8]) -> InstallationState {
        InstallationState {
            schema_version: InstallationState::SCHEMA_VERSION,
            core_version: "1.0.0".to_owned(),
            files: vec![BaselineFile {
                path: RelativePath::parse("docs/WORKFLOW.md").unwrap(),
                content: content.to_vec(),
                hash: hash_bytes(content).unwrap(),
            }],
        }
    }

    #[test]
    fn applies_and_loads_versioned_baseline_state() {
        let root = tempfile::tempdir().unwrap();
        let store = FileSystemInstallationState;
        let mutation = WorkspaceMutation::Write {
            path: RelativePath::parse("docs/WORKFLOW.md").unwrap(),
            content: b"local".to_vec(),
        };
        store
            .apply(root.path(), &state(b"base"), &[mutation])
            .unwrap();
        assert_eq!(
            fs::read(root.path().join("docs/WORKFLOW.md")).unwrap(),
            b"local"
        );
        assert_eq!(store.load(root.path()).unwrap().unwrap(), state(b"base"));
    }

    #[test]
    fn incomplete_transaction_is_rolled_back_before_new_work() {
        let root = tempfile::tempdir().unwrap();
        let store = FileSystemInstallationState;
        let path = RelativePath::parse("docs/WORKFLOW.md").unwrap();
        store
            .apply(
                root.path(),
                &state(b"base"),
                &[WorkspaceMutation::Write {
                    path: path.clone(),
                    content: b"original".to_vec(),
                }],
            )
            .unwrap();

        let state_root = state_root(root.path());
        let backup_relative = ".harness-backup/harness-core-interrupted";
        let backup = root.path().join(backup_relative);
        copy_file(
            &root.path().join(path.as_str()),
            &backup.join("files").join(path.as_str()),
        )
        .unwrap();
        copy_file(
            &state_root.join("manifest.json"),
            &backup.join("state/manifest.json"),
        )
        .unwrap();
        copy_tree(&state_root.join("base"), &backup.join("state/base")).unwrap();
        fs::write(root.path().join(path.as_str()), b"partial").unwrap();
        let journal = TransactionJournal {
            schema_version: 1,
            id: "interrupted".to_owned(),
            phase: TransactionPhase::Applying,
            backup_relative: backup_relative.to_owned(),
            state_existed: true,
            files: vec![JournalFile {
                path: path.as_str().to_owned(),
                existed: true,
            }],
        };
        write_json_atomic(&state_root.join("transaction.json"), &journal, "test").unwrap();

        assert!(store.recover_interrupted(root.path()).unwrap());
        assert_eq!(
            fs::read(root.path().join(path.as_str())).unwrap(),
            b"original"
        );
        assert!(!state_root.join("transaction.json").exists());
    }

    #[test]
    fn apply_failure_restores_workspace_and_prior_provenance() {
        let root = tempfile::tempdir().unwrap();
        let store = FileSystemInstallationState;
        let path = RelativePath::parse("docs/WORKFLOW.md").unwrap();
        store
            .apply(
                root.path(),
                &state(b"base"),
                &[WorkspaceMutation::Write {
                    path: path.clone(),
                    content: b"original".to_vec(),
                }],
            )
            .unwrap();
        let invalid = InstallationState {
            schema_version: InstallationState::SCHEMA_VERSION,
            core_version: "2.0.0".to_owned(),
            files: vec![BaselineFile {
                path: path.clone(),
                content: b"next".to_vec(),
                hash: ContentHash::parse("0".repeat(64)).unwrap(),
            }],
        };
        let result = store.apply(
            root.path(),
            &invalid,
            &[WorkspaceMutation::Write {
                path: path.clone(),
                content: b"partial".to_vec(),
            }],
        );
        assert!(result.is_err());
        assert_eq!(
            fs::read(root.path().join(path.as_str())).unwrap(),
            b"original"
        );
        assert_eq!(store.load(root.path()).unwrap().unwrap(), state(b"base"));
    }

    #[cfg(unix)]
    #[test]
    fn refuses_symlinks_in_managed_paths() {
        use std::os::unix::fs::symlink;

        let root = tempfile::tempdir().unwrap();
        let outside = tempfile::tempdir().unwrap();
        symlink(outside.path(), root.path().join("docs")).unwrap();
        let error = FileSystemInstallationState
            .validate_managed_path(
                root.path(),
                &RelativePath::parse("docs/WORKFLOW.md").unwrap(),
            )
            .unwrap_err();
        assert!(error.to_string().contains("refusing symlink"));
    }
}
