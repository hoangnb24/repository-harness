#[cfg(unix)]
use std::fs::File;
#[cfg(unix)]
use std::io::{Read, Write};
use std::path::{Component, Path, PathBuf};

use serde::{Deserialize, Serialize};

use crate::capture::hex_sha256;
use crate::{BridgeError, Result};

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct RootIdentity {
    pub device: String,
    pub inode: String,
}

pub struct SecureRoot {
    path: PathBuf,
    #[cfg(unix)]
    descriptor: std::os::fd::OwnedFd,
    #[cfg(unix)]
    stat: rustix::fs::Stat,
}

impl SecureRoot {
    pub fn open(path: &Path) -> Result<Self> {
        #[cfg(not(unix))]
        {
            let _ = path;
            Err(BridgeError::Unsupported(
                "descriptor-relative repository commands are unavailable on this platform; Phase 7 remains closed"
                    .into(),
            ))
        }
        #[cfg(unix)]
        {
            use rustix::fs::{fstat, open, Mode, OFlags};
            let descriptor = open(
                path,
                OFlags::RDONLY | OFlags::DIRECTORY | OFlags::NOFOLLOW | OFlags::CLOEXEC,
                Mode::empty(),
            )
            .map_err(|error| map_errno(".", error))?;
            let stat = fstat(&descriptor).map_err(|error| map_errno(".", error))?;
            Ok(Self {
                path: path.to_path_buf(),
                descriptor,
                stat,
            })
        }
    }

    pub fn identity(&self) -> RootIdentity {
        #[cfg(unix)]
        {
            RootIdentity {
                device: self.stat.st_dev.to_string(),
                inode: self.stat.st_ino.to_string(),
            }
        }
        #[cfg(not(unix))]
        unreachable!("non-Unix roots are never constructed")
    }

    pub fn validate_root(&self) -> Result<()> {
        #[cfg(unix)]
        {
            use rustix::fs::{fstat, open, Mode, OFlags};
            let pinned = fstat(&self.descriptor).map_err(|error| map_errno(".", error))?;
            let reopened = open(
                &self.path,
                OFlags::RDONLY | OFlags::DIRECTORY | OFlags::NOFOLLOW | OFlags::CLOEXEC,
                Mode::empty(),
            )
            .map_err(|_| BridgeError::Conflict("repository-root pathname changed".into()))?;
            let current = fstat(&reopened).map_err(|error| map_errno(".", error))?;
            if !same_identity(&self.stat, &pinned) || !same_identity(&self.stat, &current) {
                return Err(BridgeError::Conflict(
                    "repository-root identity changed during operation".into(),
                ));
            }
            Ok(())
        }
        #[cfg(not(unix))]
        unreachable!("non-Unix roots are never constructed")
    }

    #[cfg(unix)]
    pub fn root_descriptor(&self) -> &std::os::fd::OwnedFd {
        &self.descriptor
    }

    #[cfg(unix)]
    pub fn open_dir(
        &self,
        relative: &str,
        create: bool,
        sensitive: bool,
    ) -> Result<std::os::fd::OwnedFd> {
        use rustix::fs::{fchmod, fstat, fsync, mkdirat, openat, FileType, Mode, OFlags};

        validate_relative(relative)?;
        if create && relative.starts_with(".harness/recovery") {
            let kind = "recovery";
            let parent_path = format!(".harness/{kind}");
            if let Ok(parent_fd) = self.open_dir(&parent_path, false, false) {
                if !self.authenticated_custody(kind)?
                    && !self.list_names(&parent_fd, &parent_path)?.is_empty()
                {
                    return Err(BridgeError::Conflict(format!(
                        "foreign .harness/{kind} custody cannot receive bridge children"
                    )));
                }
            }
        }
        let mut parent: Option<std::os::fd::OwnedFd> = None;
        let components = relative.split('/').collect::<Vec<_>>();
        for (index, component) in components.iter().enumerate() {
            let parent_fd = parent.as_ref().unwrap_or(&self.descriptor);
            let opened = openat(
                parent_fd,
                *component,
                OFlags::RDONLY | OFlags::DIRECTORY | OFlags::NOFOLLOW | OFlags::CLOEXEC,
                Mode::empty(),
            );
            let (descriptor, created) = match opened {
                Ok(descriptor) => (descriptor, false),
                Err(error) if create && error == rustix::io::Errno::NOENT => {
                    mkdirat(parent_fd, *component, Mode::from_bits_truncate(0o700))
                        .map_err(|error| map_errno(relative, error))?;
                    fsync(parent_fd).map_err(|error| map_errno(relative, error))?;
                    let descriptor = openat(
                        parent_fd,
                        *component,
                        OFlags::RDONLY | OFlags::DIRECTORY | OFlags::NOFOLLOW | OFlags::CLOEXEC,
                        Mode::empty(),
                    )
                    .map_err(|error| map_errno(relative, error))?;
                    (descriptor, true)
                }
                Err(error) => return Err(map_errno(relative, error)),
            };
            let stat = fstat(&descriptor).map_err(|error| map_errno(relative, error))?;
            if !FileType::from_raw_mode(stat.st_mode).is_dir() {
                return Err(BridgeError::Conflict(format!(
                    "repository path component is not a directory: {relative}"
                )));
            }
            if created {
                fchmod(&descriptor, Mode::from_bits_truncate(0o700))
                    .map_err(|error| map_errno(relative, error))?;
            }
            if sensitive && index + 1 == components.len() && stat.st_mode as u32 & 0o077 != 0 {
                return Err(BridgeError::Conflict(format!(
                    "sensitive custody directory is not private 0700: {relative}"
                )));
            }
            parent = Some(descriptor);
        }
        parent.ok_or_else(|| BridgeError::Conflict("empty directory path".into()))
    }

    #[cfg(unix)]
    pub fn create_dir_exact(&self, relative: &str) -> Result<std::os::fd::OwnedFd> {
        use rustix::fs::{fchmod, fsync, mkdirat, openat, Mode, OFlags};
        let (parent, name) = self.open_parent(relative, false)?;
        mkdirat(&parent, &name, Mode::from_bits_truncate(0o700))
            .map_err(|error| map_errno(relative, error))?;
        fsync(&parent).map_err(|error| map_errno(relative, error))?;
        let descriptor = openat(
            &parent,
            &name,
            OFlags::RDONLY | OFlags::DIRECTORY | OFlags::NOFOLLOW | OFlags::CLOEXEC,
            Mode::empty(),
        )
        .map_err(|error| map_errno(relative, error))?;
        fchmod(&descriptor, Mode::from_bits_truncate(0o700))
            .map_err(|error| map_errno(relative, error))?;
        Ok(descriptor)
    }

    #[cfg(unix)]
    pub fn open_parent(
        &self,
        relative: &str,
        create: bool,
    ) -> Result<(std::os::fd::OwnedFd, String)> {
        use rustix::fs::{openat, Mode, OFlags};
        validate_relative(relative)?;
        let (parent, name) = relative.rsplit_once('/').unwrap_or(("", relative));
        let descriptor = if parent.is_empty() {
            openat(
                &self.descriptor,
                ".",
                OFlags::RDONLY | OFlags::DIRECTORY | OFlags::NOFOLLOW | OFlags::CLOEXEC,
                Mode::empty(),
            )
            .map_err(|error| map_errno(relative, error))?
        } else {
            self.open_dir(
                parent,
                create,
                parent.contains("recovery") || parent.contains("legacy"),
            )?
        };
        Ok((descriptor, name.to_owned()))
    }

    #[cfg(unix)]
    pub fn open_required_regular(&self, relative: &str) -> Result<std::os::fd::OwnedFd> {
        self.open_optional_regular(relative)?.ok_or_else(|| {
            BridgeError::Unsupported(format!("required repository input is absent: {relative}"))
        })
    }

    #[cfg(unix)]
    pub fn open_optional_regular(&self, relative: &str) -> Result<Option<std::os::fd::OwnedFd>> {
        use rustix::fs::{fstat, openat, FileType, Mode, OFlags};
        let (parent, name) = match self.open_parent(relative, false) {
            Ok(value) => value,
            Err(BridgeError::Errno(error)) if error == rustix::io::Errno::NOENT => return Ok(None),
            Err(error) => return Err(error),
        };
        let descriptor = match openat(
            &parent,
            &name,
            OFlags::RDONLY | OFlags::NOFOLLOW | OFlags::CLOEXEC,
            Mode::empty(),
        ) {
            Ok(descriptor) => descriptor,
            Err(error) if error == rustix::io::Errno::NOENT => return Ok(None),
            Err(error) => return Err(map_errno(relative, error)),
        };
        let stat = fstat(&descriptor).map_err(|error| map_errno(relative, error))?;
        if !FileType::from_raw_mode(stat.st_mode).is_file() {
            return Err(BridgeError::Conflict(format!(
                "repository input is not a regular file: {relative}"
            )));
        }
        Ok(Some(descriptor))
    }

    pub fn read(&self, relative: &str) -> Result<Vec<u8>> {
        #[cfg(unix)]
        {
            use rustix::fs::fstat;
            let descriptor = self.open_required_regular(relative)?;
            let before = fstat(&descriptor).map_err(|error| map_errno(relative, error))?;
            let mut file = File::from(descriptor);
            let mut bytes = Vec::new();
            file.read_to_end(&mut bytes)?;
            let after = fstat(&file).map_err(|error| map_errno(relative, error))?;
            if !same_file(&before, &after) || after.st_size != bytes.len() as i64 {
                return Err(BridgeError::Conflict(format!(
                    "repository file changed while reading: {relative}"
                )));
            }
            Ok(bytes)
        }
        #[cfg(not(unix))]
        unreachable!("non-Unix roots are never constructed")
    }

    pub fn read_optional(&self, relative: &str) -> Result<Option<Vec<u8>>> {
        #[cfg(unix)]
        {
            let Some(descriptor) = self.open_optional_regular(relative)? else {
                return Ok(None);
            };
            let mut file = File::from(descriptor);
            let mut bytes = Vec::new();
            file.read_to_end(&mut bytes)?;
            Ok(Some(bytes))
        }
        #[cfg(not(unix))]
        unreachable!("non-Unix roots are never constructed")
    }

    #[cfg(unix)]
    pub fn read_private_regular(&self, relative: &str, expected_len: usize) -> Result<Vec<u8>> {
        use rustix::fs::{fstat, FileType};
        let descriptor = self.open_optional_regular(relative)?.ok_or_else(|| {
            BridgeError::Conflict(format!("private evidence is absent: {relative}"))
        })?;
        let stat = fstat(&descriptor).map_err(|error| map_errno(relative, error))?;
        if !FileType::from_raw_mode(stat.st_mode).is_file()
            || stat.st_mode as u32 & 0o777 != 0o600
            || stat.st_uid != self.stat.st_uid
        {
            return Err(BridgeError::Conflict(format!(
                "private evidence has invalid owner, type, or mode: {relative}"
            )));
        }
        let mut file = File::from(descriptor);
        let mut bytes = Vec::new();
        file.read_to_end(&mut bytes)?;
        if bytes.len() != expected_len {
            return Err(BridgeError::Conflict(format!(
                "private evidence has invalid length: {relative}"
            )));
        }
        Ok(bytes)
    }

    pub fn exists(&self, relative: &str) -> Result<bool> {
        #[cfg(unix)]
        {
            Ok(self.open_optional_regular(relative)?.is_some())
        }
        #[cfg(not(unix))]
        unreachable!("non-Unix roots are never constructed")
    }

    pub fn preflight_new_file(&self, relative: &str) -> Result<()> {
        validate_output_path(relative)?;
        if self.open_optional_regular(relative)?.is_some() {
            return Err(BridgeError::Conflict(format!(
                "output destination is already occupied: {relative}"
            )));
        }
        Ok(())
    }

    pub fn write_new(&self, relative: &str, bytes: &[u8]) -> Result<()> {
        #[cfg(unix)]
        {
            use rustix::fs::{fchmod, fsync, openat, Mode, OFlags};
            let (parent, name) = self.open_parent(relative, false)?;
            let descriptor = openat(
                &parent,
                &name,
                OFlags::WRONLY | OFlags::CREATE | OFlags::EXCL | OFlags::NOFOLLOW | OFlags::CLOEXEC,
                Mode::from_bits_truncate(0o600),
            )
            .map_err(|error| map_errno(relative, error))?;
            write_checkpoint("file-open")?;
            fchmod(&descriptor, Mode::from_bits_truncate(0o600))
                .map_err(|error| map_errno(relative, error))?;
            let mut file = File::from(descriptor);
            file.write_all(bytes)?;
            write_checkpoint("file-written")?;
            file.sync_all()?;
            write_checkpoint("file-synced")?;
            fsync(&parent).map_err(|error| map_errno(relative, error))?;
            Ok(())
        }
        #[cfg(not(unix))]
        unreachable!("non-Unix roots are never constructed")
    }

    pub fn write_exact_or_new(&self, relative: &str, bytes: &[u8]) -> Result<()> {
        match self.read_optional(relative)? {
            Some(existing) if existing == bytes => Ok(()),
            Some(_) => Err(BridgeError::Conflict(format!(
                "owned evidence differs at {relative}"
            ))),
            None => self.write_new(relative, bytes),
        }
    }

    pub fn write_atomic_owned(&self, relative: &str, bytes: &[u8]) -> Result<()> {
        #[cfg(unix)]
        {
            use rustix::fs::{fchmod, fsync, openat, renameat, Mode, OFlags};
            let (parent, name) = self.open_parent(relative, false)?;
            if let Some(existing) = self.read_optional(relative)? {
                if existing.is_empty() {
                    return Err(BridgeError::Conflict(format!(
                        "owned destination unexpectedly empty: {relative}"
                    )));
                }
            }
            let temporary = format!("{name}.tmp");
            let descriptor = openat(
                &parent,
                &temporary,
                OFlags::WRONLY | OFlags::CREATE | OFlags::EXCL | OFlags::NOFOLLOW | OFlags::CLOEXEC,
                Mode::from_bits_truncate(0o600),
            )
            .map_err(|error| map_errno(relative, error))?;
            write_checkpoint("atomic-temp-open")?;
            fchmod(&descriptor, Mode::from_bits_truncate(0o600))
                .map_err(|error| map_errno(relative, error))?;
            let mut file = File::from(descriptor);
            file.write_all(bytes)?;
            write_checkpoint("atomic-temp-written")?;
            file.sync_all()?;
            renameat(&parent, &temporary, &parent, &name)
                .map_err(|error| map_errno(relative, error))?;
            write_checkpoint("atomic-renamed")?;
            fsync(&parent).map_err(|error| map_errno(relative, error))?;
            Ok(())
        }
        #[cfg(not(unix))]
        unreachable!("non-Unix roots are never constructed")
    }

    pub fn rename_no_replace(&self, source: &str, destination: &str) -> Result<()> {
        #[cfg(any(target_os = "linux", target_os = "macos"))]
        {
            use rustix::fs::{fsync, renameat_with, RenameFlags};
            let (source_parent, source_name) = self.open_parent(source, false)?;
            let (destination_parent, destination_name) = self.open_parent(destination, false)?;
            renameat_with(
                &source_parent,
                &source_name,
                &destination_parent,
                &destination_name,
                RenameFlags::NOREPLACE,
            )
            .map_err(|error| map_errno(destination, error))?;
            fsync(&source_parent).map_err(|error| map_errno(source, error))?;
            fsync(&destination_parent).map_err(|error| map_errno(destination, error))?;
            Ok(())
        }
        #[cfg(not(any(target_os = "linux", target_os = "macos")))]
        {
            let _ = (source, destination);
            Err(BridgeError::Unsupported(
                "atomic descriptor-relative no-replace is unavailable until Phase 7".into(),
            ))
        }
    }

    pub fn remove_exact(&self, relative: &str, expected_sha256: &str) -> Result<()> {
        #[cfg(unix)]
        {
            use rustix::fs::{
                fstat, fsync, openat, renameat_with, FileType, Mode, OFlags, RenameFlags,
            };
            use std::time::{SystemTime, UNIX_EPOCH};
            let lock = self.acquire_bridge_lock()?;
            let (source_parent, source_name) = self.open_parent(relative, false)?;
            let descriptor = openat(
                &source_parent,
                &source_name,
                OFlags::RDONLY | OFlags::NOFOLLOW | OFlags::CLOEXEC,
                Mode::empty(),
            )
            .map_err(|error| map_errno(relative, error))?;
            let before = fstat(&descriptor).map_err(|error| map_errno(relative, error))?;
            if !FileType::from_raw_mode(before.st_mode).is_file() {
                return Err(BridgeError::Conflict(format!(
                    "target is not a regular file: {relative}"
                )));
            }
            let bytes = self.read(relative)?;
            if hex_sha256(&bytes) != expected_sha256 {
                return Err(BridgeError::Conflict(format!(
                    "refusing to remove drifted target: {relative}"
                )));
            }
            let nonce = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .map_err(|error| BridgeError::Io(std::io::Error::other(error)))?
                .as_nanos();
            let quarantine =
                format!(".harness/recovery/v0-conversion/.rollback-quarantine-{nonce}");
            let (quarantine_parent, quarantine_name) = self.open_parent(&quarantine, false)?;
            renameat_with(
                &source_parent,
                &source_name,
                &quarantine_parent,
                &quarantine_name,
                RenameFlags::NOREPLACE,
            )
            .map_err(|error| map_errno(relative, error))?;
            let quarantined = openat(
                &quarantine_parent,
                &quarantine_name,
                OFlags::RDONLY | OFlags::NOFOLLOW | OFlags::CLOEXEC,
                Mode::empty(),
            )
            .map_err(|error| map_errno(&quarantine, error))?;
            let after = fstat(&quarantined).map_err(|error| map_errno(&quarantine, error))?;
            if !same_identity(&before, &after) {
                renameat_with(
                    &quarantine_parent,
                    &quarantine_name,
                    &source_parent,
                    &source_name,
                    RenameFlags::NOREPLACE,
                )
                .map_err(|error| map_errno(relative, error))?;
                return Err(BridgeError::Conflict(
                    "target identity changed before conditional quarantine".into(),
                ));
            }
            rustix::fs::unlinkat(
                &quarantine_parent,
                &quarantine_name,
                rustix::fs::AtFlags::empty(),
            )
            .map_err(|error| map_errno(&quarantine, error))?;
            fsync(&source_parent).map_err(|error| map_errno(relative, error))?;
            fsync(&quarantine_parent).map_err(|error| map_errno(&quarantine, error))?;
            drop(lock);
            Ok(())
        }
        #[cfg(not(unix))]
        unreachable!("non-Unix roots are never constructed")
    }

    #[cfg(unix)]
    fn acquire_bridge_lock(&self) -> Result<File> {
        use rustix::fs::{fchmod, openat, Mode, OFlags};
        let (parent, name) =
            self.open_parent(".harness/recovery/v0-conversion/.bridge.lock", true)?;
        let descriptor = openat(
            &parent,
            &name,
            OFlags::WRONLY | OFlags::CREATE | OFlags::CLOEXEC | OFlags::NOFOLLOW,
            Mode::from_bits_truncate(0o600),
        )
        .map_err(|error| map_errno(".bridge.lock", error))?;
        fchmod(&descriptor, Mode::from_bits_truncate(0o600))
            .map_err(|error| map_errno(".bridge.lock", error))?;
        let file = File::from(descriptor);
        fs2::FileExt::try_lock_exclusive(&file)
            .map_err(|error| BridgeError::Conflict(format!("bridge lock unavailable: {error}")))?;
        Ok(file)
    }

    #[cfg(unix)]
    pub fn list_names(
        &self,
        descriptor: &std::os::fd::OwnedFd,
        label: &str,
    ) -> Result<Vec<String>> {
        use rustix::fs::Dir;
        let mut names = Vec::new();
        for entry in Dir::read_from(descriptor).map_err(|error| map_errno(label, error))? {
            let entry = entry.map_err(|error| map_errno(label, error))?;
            let name = entry
                .file_name()
                .to_str()
                .map_err(|_| BridgeError::Unsupported(format!("non-UTF-8 name in {label}")))?;
            if name != "." && name != ".." {
                names.push(name.to_owned());
            }
        }
        names.sort();
        Ok(names)
    }

    #[cfg(not(unix))]
    pub fn list_names(
        &self,
        _descriptor: &std::os::fd::OwnedFd,
        _label: &str,
    ) -> Result<Vec<String>> {
        Err(BridgeError::Unsupported(
            "descriptor-relative directory enumeration is unavailable until Phase 7".into(),
        ))
    }

    #[cfg(unix)]
    pub fn authenticated_custody(&self, kind: &str) -> Result<bool> {
        let base = format!(".harness/{kind}/v0-conversion");
        let directory = match self.open_dir(&base, false, false) {
            Ok(directory) => directory,
            Err(BridgeError::Errno(error)) if error == rustix::io::Errno::NOENT => {
                return Ok(false)
            }
            Err(error) => return Err(error),
        };
        for name in self.list_names(&directory, &base)? {
            if name == "journal-auth.key" || name.ends_with(".archive-staging") {
                continue;
            }
            let journal = format!(".harness/recovery/v0-conversion/{name}/journal.json");
            if crate::journal::load_pinned(self, &name).is_ok() && self.exists(&journal)? {
                return Ok(true);
            }
        }
        Ok(false)
    }
}

#[cfg(not(unix))]
impl SecureRoot {
    pub fn open_dir(
        &self,
        _relative: &str,
        _create: bool,
        _sensitive: bool,
    ) -> Result<std::fs::File> {
        Err(BridgeError::Unsupported(
            "descriptor-relative directory custody is unavailable until Phase 7".into(),
        ))
    }

    pub fn create_dir_exact(&self, _relative: &str) -> Result<std::fs::File> {
        Err(BridgeError::Unsupported(
            "descriptor-relative directory custody is unavailable until Phase 7".into(),
        ))
    }

    pub fn open_parent(&self, _relative: &str, _create: bool) -> Result<(std::fs::File, String)> {
        Err(BridgeError::Unsupported(
            "descriptor-relative path custody is unavailable until Phase 7".into(),
        ))
    }

    pub fn open_required_regular(&self, _relative: &str) -> Result<std::fs::File> {
        Err(BridgeError::Unsupported(
            "descriptor-relative input capture is unavailable until Phase 7".into(),
        ))
    }

    pub fn open_optional_regular(&self, _relative: &str) -> Result<Option<std::fs::File>> {
        Err(BridgeError::Unsupported(
            "descriptor-relative input capture is unavailable until Phase 7".into(),
        ))
    }
}

fn validate_relative(value: &str) -> Result<()> {
    let path = Path::new(value);
    let components = value.split('/').collect::<Vec<_>>();
    if value.is_empty()
        || path.is_absolute()
        || value.contains('\\')
        || value.contains(':')
        || value.bytes().any(|byte| byte.is_ascii_control())
        || path.components().any(|component| {
            matches!(
                component,
                Component::CurDir
                    | Component::ParentDir
                    | Component::RootDir
                    | Component::Prefix(_)
            )
        })
        || components.iter().any(|component| {
            component.is_empty()
                || component.ends_with('.')
                || component.ends_with(' ')
                || component.eq_ignore_ascii_case(".git")
                || windows_device_name(component)
        })
    {
        return Err(BridgeError::Usage(
            "path must be safe and repository-relative".into(),
        ));
    }
    Ok(())
}

#[cfg(unix)]
fn write_checkpoint(name: &str) -> Result<()> {
    if std::env::var("HARNESS_V0_MIGRATE_TEST_KILL_DURING_WRITE").as_deref() == Ok(name) {
        return Err(BridgeError::KillPoint(format!("write:{name}")));
    }
    Ok(())
}

fn validate_output_path(value: &str) -> Result<()> {
    validate_relative(value)?;
    if value.starts_with(".harness/")
        || value == ".harness"
        || value.starts_with(".git/")
        || value == ".git"
    {
        return Err(BridgeError::Usage(
            "bridge output must be a repository-relative export outside custody or .git".into(),
        ));
    }
    Ok(())
}

fn windows_device_name(component: &str) -> bool {
    let stem = component.split('.').next().unwrap_or(component);
    matches!(
        stem.to_ascii_uppercase().as_str(),
        "CON" | "PRN" | "AUX" | "NUL"
    ) || (stem.len() == 4
        && (stem.starts_with("COM") || stem.starts_with("LPT"))
        && stem[3..].bytes().all(|byte| byte.is_ascii_digit()))
}

#[cfg(unix)]
fn same_identity(left: &rustix::fs::Stat, right: &rustix::fs::Stat) -> bool {
    left.st_dev == right.st_dev && left.st_ino == right.st_ino
}

#[cfg(unix)]
fn same_file(left: &rustix::fs::Stat, right: &rustix::fs::Stat) -> bool {
    same_identity(left, right)
        && left.st_size == right.st_size
        && left.st_mtime == right.st_mtime
        && left.st_mtime_nsec == right.st_mtime_nsec
        && left.st_ctime == right.st_ctime
        && left.st_ctime_nsec == right.st_ctime_nsec
}

#[cfg(unix)]
fn map_errno(path: &str, error: rustix::io::Errno) -> BridgeError {
    if matches!(
        error,
        rustix::io::Errno::LOOP
            | rustix::io::Errno::NOTDIR
            | rustix::io::Errno::ISDIR
            | rustix::io::Errno::EXIST
    ) {
        BridgeError::Conflict(format!("unsafe or prepositioned path at {path}: {error}"))
    } else {
        BridgeError::Errno(error)
    }
}
