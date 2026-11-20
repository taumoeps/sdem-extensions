# DESNRE and SDEM 0.20 — a note for the DESNRE project

*From the SDEM side (2026-11-21, `sdem-desnre` 0.9.0.dev1 on the `release/0.20` branch). Nothing here changes the site; the site's
layout and drawing are the DESNRE project's to decide.*

## What changes in SDEM 0.20

- **Data is a layer of its own** (SDEM's [data-layer spec](https://github.com/taumoeps/bian-sdem-framework/blob/release/0.20/docs/design/sdem-data-layer-spec.md), DL-01).
  With BIAN: A1 Business, A2 BIAN, **A3 Data**, A4 Application, A5 Technology. Without BIAN — SDEM's default: A1 Business, A2 Data,
  A3 Application, A4 Technology.
- **A workspace in the 0.20 form** names its files by layer (`business.json`, `data.json`, `application.json` …) and its records'
  types by id (`application.ApplicationComponent`). `sdem new` makes workspaces in this form; `sdem migrate --to 0.20` moves one.
- **An application element's access to a data entity** is a link between layers, `ACCESSED_BY` (data entity → application element),
  approved like any link between layers.

## What the publisher does now (no change to the site)

`sdem-desnre create|publish` takes a workspace in either form. A 0.20 workspace is published **as 0.19 held it** — SDEM writes that
copy (`sdem.api.export_019`), Data's records back in the Application plate and each approved `ACCESSED_BY` as access inside it — so
the site receives the **four plates it draws today**. The model is the same as the same design's in the 0.19 form (a test holds
it: every node and link the same, a few links in another order). `pull` into a 0.20 workspace is refused plainly for now.

## For the site to decide — when it is ready to show 0.20 as 0.20

1. **Five plates, or four with Data inside Application?** The Architecture view already draws Data as a sub-plate (A3-1 Data,
   A3-2 Application). Showing Data as its own plate would add a fifth plate where BIAN is on (and keep four where it is off).
2. **Labels.** In 0.20 the numbers are computed from the layers in use: Application is A4 with BIAN, A3 without; Technology A5 or A4.
   The site would take each plate's label from the model rather than from a fixed list.
3. **The model format.** A `desnre-model` version 2 could carry the layers as data (`layers: [{id, code, name}]`) and Data's plate;
   the publisher would then send a 0.20 workspace as it is, and keep sending version 1 to a site that has not moved.
4. **The workbench's changes (pull).** A change made on the site names a layer; with layer ids in the model, `pull` can apply it to
   a 0.20 workspace with SDEM's own `sdem change propose`.
5. **Designs already published** keep showing what they showed until someone publishes them again (EL-04).

When the site has decided, the publisher's part — version 2 of the model, pull for 0.20 — is a small change on this side.
