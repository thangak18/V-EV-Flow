# Product UX: Driver and Operator

## Applied design references

- [NN/g: Visual design principles](https://www.nngroup.com/articles/principles-visual-design/): establish hierarchy through type size, spacing and contrast; group related inputs and outcomes.
- [NN/g: Progressive disclosure](https://www.nngroup.com/articles/progressive-disclosure/): prioritize the immediate task and explain advanced settings when requested.
- [NN/g: Complex application design](https://www.nngroup.com/articles/complex-application-design/): make task sequences explicit and explain quantitative information in context.
- [Material: Top app bars](https://m3.material.io/components/app-bars/): identify the current workspace and keep navigation distinct from task controls.

These references guide this implementation; they do not certify usability or replace user testing.

## Two independent destinations

`/driver` is the charging journey workspace. `/operator` is the network planning workspace. The current role is identified in the header; role switching is an explicit menu rather than a two-tab strip. Both can be opened directly in separate browser tabs.

Product-facing copy avoids the word “demo”. Source labels **Dữ liệu mô phỏng / Dữ liệu minh họa / Dữ liệu thật / Dữ liệu hỗn hợp** remain truthful. No production connectivity, physical reservation, nationwide station coverage or measured accuracy is implied by the visual refresh.

## Driver flow

Choose endpoints, battery percentage and connector; explicitly request a plan. The primary station shows probability at ETA, remaining battery and extra distance. A visible **Phương án B** card explains that backup arrival time and remaining battery account for travel through the primary station. A probability is an estimate, not a physical booking.

The forecast explanation describes directional model contributions. **Cách tính & độ tin cậy** explains percentages, remaining battery, extra distance, provenance and independence assumptions in plain Vietnamese. Model versions, allocation identifiers and station IDs live in a nested verification disclosure.

## Operator flow

1. Search an area using Goong or the existing station directory; select a radius and apply. Only station coordinates within that radius contribute to the map and area KPIs. Unknown geographic coverage produces a clear no-data state, not invented stations. “Toàn bộ mạng lưới” clears the filter.
2. Apply the demand scenario to view the fixed 30-minute forecast. Risk colours and the high-risk KPI use the same 0.66 threshold. Explain the three strategies before displaying results. The reproducibility seed is labelled **Mã lần chạy** under **Thiết lập lần chạy**.
3. Choose a capacity or departure-shift experiment, select its parameters, and request before/after comparison. Summaries show improvement, deterioration or no observed change; zero is neutral. Detailed metric tables and verification are progressively disclosed.

The area filter is a **view filter**. Simulation/what-if still use the complete producer network, vehicles, seed and assumptions; that scope is stated beside their controls. It does not change backend experiment scope or imply a new local model. Shared APIs, generated types, model artifacts and simulation behavior are unchanged.

## Interaction and validation

Keep form submission explicit, cancel stale autocomplete results, preserve selected-coordinate validation, keyboard-operable controls, visible focus and reduced-motion support. Check desktop and mobile viewport overflow, error/empty/loading states, same-scenario re-selection, exact result metadata, and real-artifact Driver/Operator/what-if flows. Screenshots and local logs remain ignored artifacts; final verification records the tested revision.
