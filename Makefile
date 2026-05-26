ifeq ($(OS),Windows_NT)
	BIN_DIR := Scripts
else
	BIN_DIR := bin
endif

# Use separate environment for the package manager to allow quick clean installs.
# The local environment takes precedence over the package manager environment.
UV_PATH := $(CURDIR)/.venv_uv/$(BIN_DIR)
export PATH := $(CURDIR)/.venv/$(BIN_DIR):$(UV_PATH):$(PATH)

PYTEST := coverage run -m pytest --exitfirst --durations=10

build: deps test

# Dependencies
clean:
	rm -rf .venv
	$(UV_PATH)/uv --version || make clean_uv
	uv venv .venv

clean_uv:
	rm -rf .venv_uv .venv
	python3 -m venv .venv_uv
	python3 -m pip install uv

clean_uv_cache:
	uv clean

deps:
	uv --version || make clean
	uv sync --all-extras
	uv run python3 -m ibis_typing.type_patch

update_deps:
	uv lock --upgrade
	make clean deps

update_expected: export UPDATE_EXPECTED=Y
update_expected:
	uv run $(PYTEST) -k "test_generate_ibis_schema_packages and not test_update_expected_is_false_by_default"

# Test
test: test_unittests test_duck test_trino test_patchers test_coverage

test_unittests: lint
	uv run $(PYTEST) -m "not ibis"
test_duck: export TEST_IBIS_BACKEND=duck
test_duck:
	uv run $(PYTEST) -m "duck"
test_trino: export TEST_IBIS_BACKEND=trino
test_trino:
	uv run $(PYTEST) -m "trino"
test_patchers:
	uv run coverage run -m ibis_typing.type_patch
	uv run coverage run -m ibis_typing.ide.setup_ide
test_coverage:
	uv run coverage combine
	uv run coverage html
	uv run coverage report --skip-covered --sort=cover --fail=90

# QA
format:
	uv run ruff format
fix:
	uv run ruff check --fix
	uv run ty check --fix
fix_unsafe:
	uv run ruff check --fix --unsafe-fixes
add_noqa:
	uv run ruff check --add-noqa
	uv run ty check --add-ignore
lint:
	uv run ruff check
	uv run ruff format --check
	uv run ty check
	uv run deptry .

# IDE
setup_ide:
	uv run python3 -m ibis_typing.ide.setup_ide
setup_ide_update:
	uv run python3 -m ibis_typing.ide.setup_ide --update-templates
