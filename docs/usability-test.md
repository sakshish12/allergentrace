# Usability test

The test checks NFR-04 (a first-time owner creates a dish with five ingredients in under five minutes) and risk R6 (poor usability for non-technical users). Tasks, consent text and observation sheet are in the usability test kit.

## Deviation from the plan

The project plan foresaw five participants (two staff, three guests). Only one participant was available in the time frame. This person did the staff tasks on a laptop and then the guest tasks on a smartphone. The test is therefore a pilot: it shows the most obvious problems, but it cannot show how often they occur. Because the guest tasks came after the staff tasks, the participant already knew the application, so the guest results are optimistic. The guest tasks were also done on the menu of the test café (Café Probe 1), not on the prepared Blue Avacado menu.

## Results

✓ = without help, ~ = with an explanation, ✗ = not completed.

| Task | Result | Note |
|---|---|---|
| S1 Register and confirm the e-mail | ✓ | 1 min 15 s |
| S2 Create a dish from five ingredients | ✓ | 3 min 41 s, NFR-04 met |
| S3 Find why the dish contains milk | ✓ | Named the cream |
| S4 Remove an allergen and approve | ~ | Needed an explanation of the approval step, then approved |
| S5 Find unchecked data and the supplier | ~ | Needed an explanation, then completed the data |
| G1 Open the menu by QR code, change language | ✓ | |
| G2 Hide dishes with milk | ✓ | First load took about one minute |
| G3 Understand traces | ✓ | |
| G4 Find a dish where staff must be asked | ✓ | |

Ease of use: 4 of 7. Most difficult moment named by the participant: selecting and understanding the allergen filter. The participant said the information would be trusted once it had been explained.

## Findings and backlog items

Severity: 3 = blocks the task, 2 = slows the user down or causes errors, 1 = cosmetic.

| No | Finding | Tasks | Severity | Backlog item |
|---|---|---|---|---|
| U-1 | It was not clear what happens after an allergen is removed and where to approve it. | S4 | 2 | After a removal, say that guests keep the old declaration and link directly to Approvals. |
| U-2 | Finding unchecked ingredients and knowing what to do about them needed an explanation. | S5 | 2 | Show the unknown-data warning more prominently and explain the next steps on that page. |
| U-3 | The allergen filter on the guest menu was the most difficult moment. | G2, G3 | 2 | Add one sentence near the filter that explains "contains" and "may contain". |
| U-4 | The guest menu took about a minute to load after the server had been idle. | G2 | 2 | Known technical debt TD-01; move to a hosting plan without sleep for real use. |

## Conclusion

NFR-04 was met by the one participant. All tasks were completed, two of them only after an explanation, which shows that the approval flow and the handling of unchecked data need clearer guidance for first-time users. A test with several new participants, in particular guests who have not seen the staff side, remains an open point.
