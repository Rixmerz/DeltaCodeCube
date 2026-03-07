"""Tests for architectural pattern detection."""

import numpy as np
import pytest

from deltacodecube.cube.features.pattern_features import (
    PATTERN_DIMS,
    PATTERN_NAMES,
    extract_pattern_features,
)

REPOSITORY_CODE = """
class UserRepository:
    def find_by_id(self, user_id):
        return self.db.query("SELECT * FROM users WHERE id = ?", user_id)

    def find_all(self):
        return self.db.query("SELECT * FROM users")

    def create(self, name, email):
        return self.db.execute("INSERT INTO users VALUES (?, ?)", name, email)

    def update(self, user_id, data):
        self.db.execute("UPDATE users SET name=? WHERE id=?", data['name'], user_id)

    def delete(self, user_id):
        self.db.execute("DELETE FROM users WHERE id=?", user_id)
"""

TEST_CODE = """
import pytest

class TestUserService:
    def test_create_user(self):
        user = service.create("Alice")
        assert user.name == "Alice"

    def test_delete_user(self):
        result = service.delete(1)
        assert result is True

    def test_find_user_not_found(self):
        with pytest.raises(ValueError):
            service.find(999)
"""

CONTROLLER_CODE = """
from flask import request, jsonify

@app.route('/users', methods=['POST'])
def create_user():
    data = request.get_json()
    user = service.create(data['name'])
    return jsonify(user), 201

@app.route('/users/<int:id>', methods=['GET'])
def get_user(id):
    user = service.find(id)
    if not user:
        return jsonify({"error": "Not found"}), 404
    return jsonify(user)
"""

MIGRATION_CODE = """
def upgrade():
    op.create_table('users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(100)),
    )

def downgrade():
    op.drop_table('users')
"""

CONFIG_CODE = """
# Application config settings
DATABASE_URL = "postgresql://localhost/mydb"
SECRET_KEY = "super-secret"
DEBUG = True
MAX_CONNECTIONS = 10
CACHE_TTL = 3600
"""


JSX_COMPONENT_CODE = """
import React from 'react';

export function ControlBar({ onToggle, theme }) {
    return (
        <div className="control-bar">
            <DropdownItem
                label="Enable workflow"
                trigger={onToggle}
                icon="workflow"
                value="active"
            />
            <DropdownItem
                label="Dark mode"
                trigger={theme.toggleDarkMode}
                icon="moon"
                size="large"
            />
            <DropdownSection title="Actions">
                <DropdownItem label="Reset" icon="refresh" />
                <DropdownItem label="Export" icon="download" />
            </DropdownSection>
            <button onClick={onToggle}>Toggle</button>
        </div>
    );
}
"""

SERVICE_WITH_INTERFACES_CODE = """
import { invoke } from '@tauri-apps/api/core';

interface WorkflowConfig {
    enabled: boolean;
    enforcer: boolean;
}

interface HookResult {
    success: boolean;
    message: string;
}

type HookAction = 'install' | 'uninstall' | 'sync';

export async function syncWorkflowHooks(projectPath: string, enabled: boolean): Promise<HookResult> {
    const config: WorkflowConfig = { enabled, enforcer: enabled };
    const result = await invoke('write_file', { path: projectPath, content: JSON.stringify(config) });
    return { success: true, message: 'Hooks synced' };
}

export async function getEnforcerEnabled(projectPath: string): Promise<boolean> {
    const raw = await invoke('read_file', { path: projectPath });
    const config = JSON.parse(raw as string) as WorkflowConfig;
    return config.enforcer;
}

export async function installHook(projectPath: string, hookName: string): Promise<HookResult> {
    await invoke('create_dir', { path: projectPath });
    await invoke('write_file', { path: `${projectPath}/${hookName}`, content: '#!/bin/sh' });
    return { success: true, message: `Hook ${hookName} installed` };
}

export async function uninstallHook(projectPath: string, hookName: string): Promise<HookResult> {
    await invoke('remove_file', { path: `${projectPath}/${hookName}` });
    return { success: true, message: `Hook ${hookName} uninstalled` };
}

// More service logic...
export function validateConfig(config: WorkflowConfig): boolean {
    return config.enabled !== undefined && config.enforcer !== undefined;
}
""" + "// padding\n" * 30

ZOD_SCHEMA_CODE = """
import { z } from 'zod';

export const userSchema = z.object({
    name: z.string().min(1).describe('User full name'),
    email: z.string().email().describe('User email address'),
    age: z.number().int().positive().describe('User age in years'),
    role: z.enum(['admin', 'user', 'guest']).describe('User role'),
});

export const configSchema = z.object({
    theme: z.string().describe('UI theme name'),
    language: z.string().describe('Preferred language'),
    notifications: z.boolean().describe('Enable notifications'),
});

export type User = z.infer<typeof userSchema>;
export type Config = z.infer<typeof configSchema>;
"""

TEMPLATE_STRING_ENTRYPOINT_CODE = """
import { invoke } from '@tauri-apps/api/core';

export async function installPythonHook(projectPath: string): Promise<void> {
    const hookContent = `#!/usr/bin/env python3
import json
import sys

def main():
    data = json.loads(sys.stdin.read())
    print(json.dumps({"decision": "approve"}))

if __name__ == "__main__":
    main()
`;
    await invoke('write_file', { path: projectPath, content: hookContent });
}

export async function generateScript(name: string): Promise<string> {
    return `
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('name')
    args = parser.parse_args()
    print(f"Hello {args.name}")

if __name__ == "__main__":
    main()
`;
}
"""


class TestPatternFeatures:
    def test_returns_correct_dims(self):
        features = extract_pattern_features(REPOSITORY_CODE, ".py")
        assert features.shape == (PATTERN_DIMS,)
        assert features.dtype == np.float64

    def test_repository_detected(self):
        features = extract_pattern_features(REPOSITORY_CODE, ".py")
        # is_repository is index 0
        assert features[0] > 0.5, f"Repository score too low: {features[0]}"

    def test_test_file_detected(self):
        features = extract_pattern_features(TEST_CODE, ".py")
        # is_test is index 6
        assert features[6] > 0.5, f"Test score too low: {features[6]}"

    def test_controller_detected(self):
        features = extract_pattern_features(CONTROLLER_CODE, ".py")
        # is_controller is index 1
        assert features[1] > 0.3, f"Controller score too low: {features[1]}"

    def test_migration_detected(self):
        features = extract_pattern_features(MIGRATION_CODE, ".py")
        # is_migration is index 9
        assert features[9] > 0.5, f"Migration score too low: {features[9]}"

    def test_config_detected(self):
        features = extract_pattern_features(CONFIG_CODE, ".py")
        # is_config is index 5
        assert features[5] > 0.3, f"Config score too low: {features[5]}"

    def test_scores_bounded(self):
        features = extract_pattern_features(REPOSITORY_CODE, ".py")
        assert np.all(features >= 0.0)
        assert np.all(features <= 1.0)

    def test_deterministic(self):
        f1 = extract_pattern_features(TEST_CODE, ".py")
        f2 = extract_pattern_features(TEST_CODE, ".py")
        np.testing.assert_array_equal(f1, f2)

    def test_empty_content(self):
        features = extract_pattern_features("", ".py")
        assert features.shape == (PATTERN_DIMS,)
        assert np.all(features == 0.0)

    def test_repository_not_test(self):
        features = extract_pattern_features(REPOSITORY_CODE, ".py")
        assert features[0] > features[6], "Repository should score higher than test"

    def test_test_not_repository(self):
        features = extract_pattern_features(TEST_CODE, ".py")
        assert features[6] > features[0], "Test should score higher than repository"

    def test_mixed_code_has_few_dominant_patterns(self):
        """A generic service file should not trigger 3+ patterns above 0.5."""
        generic_service = """
class UserService:
    def __init__(self, db):
        self.db = db

    def create_user(self, name, email):
        user = User(name=name, email=email)
        self.db.add(user)
        return user

    def get_user(self, user_id):
        return self.db.query(User).get(user_id)

    def delete_user(self, user_id):
        user = self.get_user(user_id)
        self.db.delete(user)
        return True

    def update_user(self, user_id, data):
        user = self.get_user(user_id)
        user.name = data.get('name', user.name)
        self.db.commit()
        return user
"""
        features = extract_pattern_features(generic_service, ".py")
        high_scores = sum(1 for f in features if f > 0.5)
        assert high_scores <= 2, (
            f"Expected at most 2 patterns > 0.5, got {high_scores}: "
            f"{[(PATTERN_NAMES[i], round(features[i], 3)) for i in range(len(features)) if features[i] > 0.5]}"
        )

    def test_jsx_not_config(self):
        """JSX components with props like label=, trigger= should not be is_config."""
        features = extract_pattern_features(JSX_COMPONENT_CODE, ".tsx")
        # is_config is index 5
        assert features[5] < 0.5, (
            f"JSX component should not be detected as config, got is_config={features[5]:.3f}"
        )

    def test_service_with_interfaces_not_types_only(self):
        """A service file with a few interfaces + lots of logic should not be is_types_only."""
        features = extract_pattern_features(SERVICE_WITH_INTERFACES_CODE, ".ts")
        # is_types_only is index 7
        assert features[7] < 0.3, (
            f"Service with few interfaces should not be types_only, got is_types_only={features[7]:.3f}"
        )

    def test_zod_describe_not_test(self):
        """Zod schemas with .describe() should not be detected as test files."""
        features = extract_pattern_features(ZOD_SCHEMA_CODE, ".ts")
        # is_test is index 6
        assert features[6] < 0.5, (
            f"Zod schema should not be detected as test, got is_test={features[6]:.3f}"
        )

    def test_template_string_not_entrypoint(self):
        """TS files with Python code in template strings should not be is_entrypoint."""
        features = extract_pattern_features(TEMPLATE_STRING_ENTRYPOINT_CODE, ".ts")
        # is_entrypoint is index 8
        assert features[8] < 0.3, (
            f"Template string with Python code should not be entrypoint, got is_entrypoint={features[8]:.3f}"
        )
