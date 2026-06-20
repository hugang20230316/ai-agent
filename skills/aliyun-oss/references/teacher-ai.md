# teacher-ai OSS Reference

Read this when the user asks for teacher-ai test-environment OSS files by workGuid, work URL, answer sheet, template, student upload, scan image, or `info.json`.

## Target Mapping

- Logical bucket in teacher-ai code: `7netomr`
- Test bucket format from local config: logical bucket plus environment suffix
- Test object base prefix: `edumaterials/work2images/work3/<workGuid>/`
- Template directory spelling used by the project: `templete/`
- Common template info key: `edumaterials/work2images/work3/<workGuid>/templete/info.json`

The real bucket and endpoint must be read from the local teacher-ai config at runtime. Do not hardcode credentials or copy them into this skill.

## Common Lookups

- Work root: list `edumaterials/work2images/work3/<workGuid>/`
- Template files: list `edumaterials/work2images/work3/<workGuid>/templete/`
- Template metadata: read `templete/info.json`
- Markdown or JSON aids: read `templete/score.md`, `templete/t.json`, or other small text files when present
- Images or scans: list first, then download selected image objects to `/tmp/oss-workguid/<workGuid>/`

## Evidence to Report

For a normal lookup, report only:

- bucket
- prefix or key
- object count
- file names or relative paths
- selected `info.json` summary fields
- local temp file path for downloads

Do not report:

- AccessKey, Secret, STS token, Authorization header
- signed URL query params
- raw signed URL
- local config snippets containing credentials

## Fallbacks

- If a user gives a signed HTTP URL, extract the object key from the URL path and the workGuid from `/work2images/work3/<workGuid>/`.
- If a requested object is missing, list the parent prefix before concluding the workGuid has no files.
- If the object list is large, show counts and the most relevant relative paths instead of dumping every key.
