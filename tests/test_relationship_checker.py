import json
import csv

from vsf_profiler.cli import run_pipeline
from vsf_profiler.demo_data import create_small_demo


def test_relationship_checker_finds_orphans(tmp_path):
    data_dir = create_small_demo(tmp_path / "demo")
    out_dir = tmp_path / "out"

    run_pipeline(
        dbml_path=data_dir / "schema.dbml",
        csv_dir=data_dir / "csv",
        rules_path=data_dir / "rules.yaml",
        target="order_reviews.review_score",
        out_dir=out_dir,
    )

    issues = json.loads((out_dir / "issues.json").read_text())
    orphan_issues = [issue for issue in issues if issue["issue_type"] == "ORPHAN_FOREIGN_KEY"]
    assert orphan_issues
    assert any(issue["table"] == "orders" and issue["parent_table"] == "customers" for issue in orphan_issues)


def test_extended_relationship_cardinality_composite_fk_and_junction_detection(tmp_path):
    root = tmp_path / "relationships"
    csv_dir = root / "csv"
    csv_dir.mkdir(parents=True)
    schema_path = root / "schema.dbml"
    schema_path.write_text(
        """
        Table users {
          user_id varchar [pk, not null]
        }

        Table user_profiles {
          user_id varchar [pk, not null]
        }

        Table companies {
          company_id varchar [pk, not null]
        }

        Table company_profiles {
          profile_id varchar [pk, not null]
          company_id varchar
        }

        Table departments {
          department_id varchar [pk, not null]
        }

        Table employees {
          employee_id varchar [pk, not null]
          department_id varchar
        }

        Table customers {
          customer_id varchar [pk, not null]
        }

        Table orders {
          order_id varchar [pk, not null]
          customer_id varchar
        }

        Table bad_customers {
          customer_id varchar
          name varchar
        }

        Table bad_orders {
          order_id varchar [pk, not null]
          customer_id varchar
        }

        Table order_lines {
          order_id varchar
          line_no varchar
          product_id varchar
          indexes {
            (order_id, line_no) [pk]
          }
        }

        Table shipments {
          order_id varchar
          line_no varchar
          shipped_at varchar
        }

        Table students {
          student_id varchar [pk, not null]
        }

        Table courses {
          course_id varchar [pk, not null]
        }

        Table enrollments {
          student_id varchar
          course_id varchar
          indexes {
            (student_id, course_id) [pk]
          }
        }

        Ref: users.user_id - user_profiles.user_id
        Ref: companies.company_id - company_profiles.company_id
        Ref: departments.department_id < employees.department_id
        Ref: orders.customer_id > customers.customer_id
        Ref: bad_orders.customer_id > bad_customers.customer_id
        Ref: shipments.(order_id, line_no) > order_lines.(order_id, line_no)
        Ref: enrollments.student_id > students.student_id
        Ref: enrollments.course_id > courses.course_id
        """
    )
    _write_csv(csv_dir / "users.csv", ["user_id"], [["U1"], ["U2"]])
    _write_csv(csv_dir / "user_profiles.csv", ["user_id"], [["U1"], ["U2"]])
    _write_csv(csv_dir / "companies.csv", ["company_id"], [["COMP1"], ["COMP2"]])
    _write_csv(
        csv_dir / "company_profiles.csv",
        ["profile_id", "company_id"],
        [["CP1", "COMP1"], ["CP2", "COMP1"], ["CP3", "COMP2"]],
    )
    _write_csv(csv_dir / "departments.csv", ["department_id"], [["D1"], ["D2"]])
    _write_csv(
        csv_dir / "employees.csv",
        ["employee_id", "department_id"],
        [["E1", "D1"], ["E2", "D1"], ["E3", "D2"]],
    )
    _write_csv(csv_dir / "customers.csv", ["customer_id"], [["C1"], ["C2"]])
    _write_csv(
        csv_dir / "orders.csv",
        ["order_id", "customer_id"],
        [["O1", "C1"], ["O2", "C1"], ["O3", "C2"]],
    )
    _write_csv(
        csv_dir / "bad_customers.csv",
        ["customer_id", "name"],
        [["C9", "first"], ["C9", "duplicate"]],
    )
    _write_csv(csv_dir / "bad_orders.csv", ["order_id", "customer_id"], [["BO1", "C9"]])
    _write_csv(
        csv_dir / "order_lines.csv",
        ["order_id", "line_no", "product_id"],
        [["O1", "1", "P1"], ["O1", "2", "P2"]],
    )
    _write_csv(
        csv_dir / "shipments.csv",
        ["order_id", "line_no", "shipped_at"],
        [["O1", "1", "2024-01-01"], ["O1", "2", "2024-01-02"]],
    )
    _write_csv(csv_dir / "students.csv", ["student_id"], [["S1"], ["S2"]])
    _write_csv(csv_dir / "courses.csv", ["course_id"], [["COURSE1"], ["COURSE2"]])
    _write_csv(
        csv_dir / "enrollments.csv",
        ["student_id", "course_id"],
        [["S1", "COURSE1"], ["S1", "COURSE2"], ["S2", "COURSE1"]],
    )

    out_dir = tmp_path / "out"
    run_pipeline(
        dbml_path=schema_path,
        csv_dir=csv_dir,
        rules_path=None,
        target=None,
        out_dir=out_dir,
    )

    schema_evaluation = json.loads((out_dir / "schema_evaluation.json").read_text())
    relationship_graph = json.loads((out_dir / "relationship_graph.json").read_text())
    report_md = (out_dir / "report.md").read_text()

    assert schema_evaluation["summary"]["relationship_cardinality_counts"] == {
        "MANY_TO_ONE": 5,
        "ONE_TO_MANY": 1,
        "ONE_TO_ONE": 2,
    }
    assert schema_evaluation["summary"]["composite_relationship_count"] == 1
    assert schema_evaluation["summary"]["junction_table_count"] == 1
    assert schema_evaluation["junction_tables"][0]["table"] == "enrollments"

    one_to_one = _edge(relationship_graph, "user_profiles", "users")
    assert one_to_one["declared_cardinality"] == "ONE_TO_ONE"
    assert one_to_one["cardinality"] == "ONE_TO_ONE"
    assert one_to_one["observed_cardinality"] == "ONE_TO_ONE"
    assert one_to_one["status"] == "valid"

    invalid_one_to_one = _edge(relationship_graph, "company_profiles", "companies")
    assert invalid_one_to_one["declared_cardinality"] == "ONE_TO_ONE"
    assert invalid_one_to_one["observed_cardinality"] == "MANY_TO_ONE"
    assert invalid_one_to_one["status"] == "invalid"
    assert invalid_one_to_one["status_reason"] == "child foreign key is not unique for one-to-one"
    assert invalid_one_to_one["metrics"]["child_duplicate_count"] == 2
    assert any(
        link["issue_type"] == "CHILD_RELATIONSHIP_DUPLICATE"
        for link in invalid_one_to_one["evidence_links"]
    )

    one_to_many = _edge(relationship_graph, "employees", "departments")
    assert one_to_many["dbml_operator"] == "<"
    assert one_to_many["declared_cardinality"] == "ONE_TO_MANY"
    assert one_to_many["observed_cardinality"] == "MANY_TO_ONE"
    assert one_to_many["status"] == "valid"

    many_to_one = _edge(relationship_graph, "orders", "customers")
    assert many_to_one["declared_cardinality"] == "MANY_TO_ONE"
    assert many_to_one["observed_cardinality"] == "MANY_TO_ONE"
    assert many_to_one["status"] == "valid"

    invalid_parent = _edge(relationship_graph, "bad_orders", "bad_customers")
    assert invalid_parent["status"] == "invalid"
    assert invalid_parent["metrics"]["parent_duplicate_count"] == 2
    assert invalid_parent["cardinality"] == "UNKNOWN_INVALID_PARENT_KEY"

    composite = _edge(relationship_graph, "shipments", "order_lines")
    assert composite["source_columns"] == ["order_id", "line_no"]
    assert composite["target_columns"] == ["order_id", "line_no"]
    assert composite["metrics"]["join_coverage"] == 1.0
    assert composite["status"] == "valid"

    assert relationship_graph["summary"]["junction_table_count"] == 1
    assert relationship_graph["junction_tables"][0]["table"] == "enrollments"
    assert relationship_graph["many_to_many_relationships"] == [
        {
            "relationship_type": "inferred_many_to_many",
            "cardinality": "MANY_TO_MANY",
            "status": "detected",
            "left_table": "courses",
            "right_table": "students",
            "junction_table": "enrollments",
        }
    ]
    assert "ONE_TO_ONE" in report_md
    assert "ONE_TO_MANY" in report_md
    assert "enrollments" in report_md


def _edge(graph: dict, source_table: str, target_table: str) -> dict:
    return next(
        edge
        for edge in graph["edges"]
        if edge["source_table"] == source_table and edge["target_table"] == target_table
    )


def _write_csv(path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)
