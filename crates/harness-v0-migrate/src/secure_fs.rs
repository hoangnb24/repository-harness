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

    pub fn exists(&self, relative: &str) -> Result<bool> {
        #[cfg(unix)]
        {
            Ok(self.open_optional_regular(relative)?.is_some())
        }
        #[cfg(not(unix))]
        unreachable!("non-Unix roots are never constructed")
    }

    pub fn preflight_new_file(&self, relative: &str) -> Result<()> {
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
            fchmod(&descriptor, Mode::from_bits_truncate(0o600))
                .map_err(|error| map_errno(relative, error))?;
            let mut file = File::from(descriptor);
            file.write_all(bytes)?;
            file.sync_all()?;
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
            fchmod(&descriptor, Mode::from_bits_truncate(0o600))
                .map_err(|error| map_errno(relative, error))?;
            let mut file = File::from(descriptor);
            file.write_all(bytes)?;
            file.sync_all()?;
            renameat(&parent, &temporary, &parent, &name)
                .map_err(|error| map_errno(relative, error))?;
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
            use rustix::fs::{fsync, unlinkat, AtFlags};
            let bytes = self.read(relative)?;
            if hex_sha256(&bytes) != expected_sha256 {
                return Err(BridgeError::Conflict(format!(
                    "refusing to remove drifted target: {relative}"
                )));
            }
            let (parent, name) = self.open_parent(relative, false)?;
            unlinkat(&parent, &name, AtFlags::empty())
                .map_err(|error| map_errno(relative, error))?;
            fsync(&parent).map_err(|error| map_errno(relative, error))?;
            Ok(())
        }
        #[cfg(not(unix))]
        unreachable!("non-Unix roots are never constructed")
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
}

fn validate_relative(value: &str) -> Result<()> {
    let path = Path::new(value);
    if value.is_empty()
        || path.is_absolute()
        || path.components().any(|component| {
            matches!(
                component,
                Component::ParentDir | Component::RootDir | Component::Prefix(_)
            )
        })
    {
        return Err(BridgeError::Usage(
            "path must be safe and repository-relative".into(),
        ));
    }
    Ok(())
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
