use std::fs;
use std::path::{Path, PathBuf};

#[test]
fn inward_layers_do_not_import_outward_layers_or_frameworks() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("src");
    assert_forbidden(
        &root.join("domain"),
        &[
            "crate::application",
            "crate::infrastructure",
            "crate::interface",
            "serde",
            "clap",
            "fs2",
            "std::fs",
            "std::process",
        ],
    );
    assert_forbidden(
        &root.join("application"),
        &[
            "crate::infrastructure",
            "crate::interface",
            "serde",
            "clap",
            "fs2",
            "std::fs",
            "std::process",
        ],
    );
    assert_forbidden(&root.join("infrastructure"), &["crate::interface"]);
    assert_forbidden(&root.join("interface"), &["crate::infrastructure"]);
}

#[test]
fn composition_root_is_the_only_layer_wiring_infrastructure_to_interface() {
    let main =
        fs::read_to_string(PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("src/main.rs")).unwrap();
    assert!(main.contains("harness::infrastructure"));
    assert!(main.contains("harness::interface"));
    assert!(main.contains("CoreApplication::new"));
    assert!(main.contains("SelfUpdateApplication::new"));
}

fn assert_forbidden(root: &Path, forbidden: &[&str]) {
    for entry in fs::read_dir(root).unwrap() {
        let path = entry.unwrap().path();
        if path.extension().and_then(|value| value.to_str()) != Some("rs") {
            continue;
        }
        let source = fs::read_to_string(&path).unwrap();
        for pattern in forbidden {
            assert!(
                !source.contains(pattern),
                "{} imports forbidden dependency {pattern}",
                path.display()
            );
        }
    }
}
