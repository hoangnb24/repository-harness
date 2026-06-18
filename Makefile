PYTHON ?= python3
PLAYWRIGHT_BIN := node_modules/.bin/playwright

.PHONY: install demo-small demo-full benchmark-small benchmark-large download-olist demo-olist postgres-smoke mysql-smoke web-demo web-runner test

install:
	$(PYTHON) -m pip install -e ".[dev]"

demo-small:
	vsf-profiler demo create-small --out data/demo_small
	vsf-profiler run \
		--dbml data/demo_small/schema.dbml \
		--csv-dir data/demo_small/csv \
		--rules data/demo_small/rules.yaml \
		--target order_reviews.review_score \
		--out outputs/demo_small

demo-full:
	vsf-profiler doctor
	$(MAKE) demo-small
	vsf-profiler package \
		--input outputs/demo_small \
		--output outputs/demo_small_package \
		--zip \
		--pdf \
		--force
	$(PYTHON) scripts/verify_vsf_artifacts.py \
		--run-dir outputs/demo_small \
		--package-dir outputs/demo_small_package \
		--zip-path outputs/demo_small_package.zip
	@if command -v node >/dev/null 2>&1 && [ -x "$(PLAYWRIGHT_BIN)" ]; then \
		echo "Running Playwright dashboard E2E..."; \
		npm run test:e2e:dashboard; \
	else \
		echo "Skipping Playwright dashboard E2E: node or local Playwright is not present."; \
	fi
	@echo "Demo full outputs:"
	@echo "  Report HTML: outputs/demo_small/report.html"
	@echo "  Report MD: outputs/demo_small/report.md"
	@echo "  Package index: outputs/demo_small_package/index.html"
	@echo "  Export manifest: outputs/demo_small_package/export_manifest.json"
	@echo "  PDF report: outputs/demo_small_package/analysis_report.pdf"
	@echo "  Package zip: outputs/demo_small_package.zip"

benchmark-small:
	$(PYTHON) scripts/benchmark_large_dataset.py \
		--work-dir outputs/benchmark_ci \
		--rows 600 \
		--tables 7 \
		--max-analysis-rows 120 \
		--max-feature-columns 4 \
		--force

benchmark-large:
	$(PYTHON) scripts/benchmark_large_dataset.py \
		--work-dir outputs/benchmark_large \
		--rows 50000 \
		--tables 8 \
		--max-analysis-rows 5000 \
		--max-feature-columns 10 \
		--force

download-olist:
	vsf-profiler demo download-olist --out data/olist

demo-olist:
	vsf-profiler demo run-olist \
		--csv-dir data/olist \
		--out outputs/olist_demo

postgres-smoke:
	$(PYTHON) -m pytest -q tests/test_postgres_acceptance.py

mysql-smoke:
	$(PYTHON) -m pytest -q tests/test_mysql_acceptance.py

web-demo:
	$(PYTHON) -m http.server 8080 --directory web

web-runner:
	vsf-profiler web --port 8765

test:
	pytest -q
