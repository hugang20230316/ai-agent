# Bug Skill Regression Notes

## Contract Test Routine

After editing this skill, verify both the rule text and the tracker fetch path:

```console
python3 scripts/diagnose_bug_config.py
python3 scripts/test_bug_skill_contract.py
python3 scripts/test_bug_skill_contract.py --live-bug <known-readable-bug-id>
python3 scripts/test_bug_skill_contract.py --live-url <known-readable-bug-url>
```

The checks cover local login config loading, required output sections, `teacherGuid`/`taskGuid` reproduction fields, and ZenTao bug ID/URL fetch behavior without inline credentials.

Keep bug-skill-specific test notes, fixtures, and cleanup guidance under this skill directory so they can be found and removed with the skill.
