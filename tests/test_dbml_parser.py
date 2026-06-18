import pytest

from vsf_profiler.dbml_parser import DbmlParseError, parse_dbml_text, parse_dbml_text_with_report


def test_parse_inline_refs_and_composite_pk():
    schema = parse_dbml_text(
        """
        Table customers {
          customer_id varchar [pk, not null]
        }

        Table order_items {
          order_id varchar [ref: > orders.order_id]
          order_item_id int
          product_id varchar

          indexes {
            (order_id, order_item_id) [pk]
          }
        }

        Table orders {
          order_id varchar [pk, not null]
          customer_id varchar
        }

        Ref: orders.customer_id > customers.customer_id
        """
    )

    assert set(schema.tables) == {"customers", "order_items", "orders"}
    assert schema.tables["customers"].columns["customer_id"].is_pk is True
    assert schema.tables["order_items"].primary_key == ["order_id", "order_item_id"]
    assert schema.tables["orders"].columns["customer_id"].foreign_key.parent_table == "customers"
    assert {
        (rel.child_table, rel.child_column, rel.parent_table, rel.parent_column)
        for rel in schema.relationships
    } == {
        ("order_items", "order_id", "orders", "order_id"),
        ("orders", "customer_id", "customers", "customer_id"),
    }


def test_parse_inline_foreign_key_contract():
    schema = parse_dbml_text(
        """
        Table customers {
          customer_id varchar [pk, not null]
        }

        Table orders {
          order_id varchar [pk, not null]
          customer_id varchar [ref: > customers.customer_id]
        }
        """
    )

    fk = schema.tables["orders"].columns["customer_id"].foreign_key
    assert fk is not None
    assert fk.parent_table == "customers"
    assert fk.parent_column == "customer_id"


def test_parse_ref_direction_variants_and_composite_foreign_key():
    schema = parse_dbml_text(
        """
        Table users {
          user_id varchar [pk, not null]
        }

        Table user_profiles {
          user_id varchar [pk, not null]
        }

        Table departments {
          department_id varchar [pk, not null]
        }

        Table employees {
          employee_id varchar [pk, not null]
          department_id varchar
        }

        Table order_lines {
          order_id varchar
          line_no varchar
          indexes {
            (order_id, line_no) [pk]
          }
        }

        Table shipments {
          order_id varchar
          line_no varchar
        }

        Ref: users.user_id - user_profiles.user_id
        Ref: departments.department_id < employees.department_id
        Ref: shipments.(order_id, line_no) > order_lines.(order_id, line_no)
        """
    )

    one_to_one = next(rel for rel in schema.relationships if rel.dbml_operator == "-")
    assert one_to_one.child_table == "user_profiles"
    assert one_to_one.parent_table == "users"
    assert one_to_one.declared_cardinality == "ONE_TO_ONE"

    one_to_many = next(rel for rel in schema.relationships if rel.dbml_operator == "<")
    assert one_to_many.child_table == "employees"
    assert one_to_many.child_column == "department_id"
    assert one_to_many.parent_table == "departments"
    assert one_to_many.declared_cardinality == "ONE_TO_MANY"

    composite = next(rel for rel in schema.relationships if len(rel.child_columns) == 2)
    assert composite.child_table == "shipments"
    assert composite.child_columns == ["order_id", "line_no"]
    assert composite.parent_table == "order_lines"
    assert composite.parent_columns == ["order_id", "line_no"]
    assert composite.declared_cardinality == "MANY_TO_ONE"


def test_parse_realistic_dbml_constructs_and_diagnostics():
    result = parse_dbml_text_with_report(
        """
        Project "Commerce Warehouse" {
          database_type: 'PostgreSQL'
          Note: 'Operational reporting schema'
        }

        Enum order_status {
          pending
          paid [note: 'payment received']
          cancelled
        }

        TableGroup "commerce core" {
          "sales"."customers"
          "sales"."orders"
        }

        Table "sales"."customers" as C [headercolor: #79AD51] {
          "customer id" varchar [pk, not null, note: 'stable customer key']
          email varchar [unique]
          status order_status [default: 'pending']

          indexes {
            (email) [unique, name: 'idx_customer_email']
          }
        }

        Table "sales"."orders" {
          "order id" varchar
          "line no" int
          "customer id" varchar [ref: > "sales"."customers"."customer id"]
          "order date" timestamp [default: `now()`]

          indexes {
            ("order id", "line no") [pk]
            ("customer id", "order date") [unique]
            (`lower("customer id")`) [name: 'idx_customer_expr']
          }
        }

        Ref order_customer {
          "sales"."orders"."customer id" > "sales"."customers"."customer id" [delete: cascade]
        }
        """
    )

    schema = result.schema
    report = result.report

    assert set(schema.tables) == {"sales.customers", "sales.orders"}
    assert schema.tables["sales.customers"].columns["customer id"].is_pk is True
    assert schema.tables["sales.customers"].columns["email"].unique is True
    assert schema.tables["sales.orders"].primary_key == ["order id", "line no"]
    assert schema.tables["sales.orders"].unique_constraints == [["customer id", "order date"]]
    assert {
        (rel.child_table, rel.child_columns[0], rel.parent_table, rel.parent_columns[0])
        for rel in schema.relationships
    } == {
        ("sales.orders", "customer id", "sales.customers", "customer id"),
    }

    assert report["status"] == "parsed_with_warnings"
    assert report["counts"]["projects"] == 1
    assert report["counts"]["enums"] == 1
    assert report["counts"]["enum_values"] == 3
    assert report["counts"]["table_groups"] == 1
    assert report["counts"]["tables"] == 2
    assert report["counts"]["columns"] == 7
    assert report["counts"]["indexes"] == 4
    assert report["counts"]["composite_primary_indexes"] == 1
    assert report["counts"]["composite_unique_indexes"] == 1
    assert report["counts"]["defaults"] == 2
    assert report["counts"]["notes"] >= 2
    assert any(
        item["code"] == "UNSUPPORTED_INDEX_EXPRESSION"
        for item in report["unsupported_constructs"]
    )


def test_unsupported_dbml_constructs_are_reported_without_blocking_parse():
    result = parse_dbml_text_with_report(
        """
        Table users {
          id int [pk]
          indexes {
            `lower(id)` [name: 'idx_expr']
          }
        }

        TablePartial audit_columns {
          created_at timestamp
        }

        Ref: users.id <> groups.user_id
        """
    )

    assert set(result.schema.tables) == {"users"}
    codes = {item["code"] for item in result.report["unsupported_constructs"]}
    assert "UNSUPPORTED_TOP_LEVEL_BLOCK" in codes
    assert "UNSUPPORTED_INDEX_EXPRESSION" in codes
    assert "UNSUPPORTED_REF_OPERATOR" in codes
    assert result.report["status"] == "parsed_with_warnings"


def test_malformed_dbml_raises_parser_error_with_context():
    with pytest.raises(DbmlParseError, match="Unclosed Table block"):
        parse_dbml_text_with_report(
            """
            Table users {
              id int [pk]
            """
        )
