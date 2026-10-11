export function PressureLegend() {
  return (
    <aside className="pressure-legend" aria-label="Pressure legend">
      <p className="eyebrow">Pressure proxy</p>
      <p>
        `pressure_score ≈ 1 − p_available` for a fixed horizon. Higher score
        means higher risk of no free port — not a measured traffic volume.
      </p>
      <ul>
        <li>
          <span className="swatch swatch--low" aria-hidden /> Low risk
        </li>
        <li>
          <span className="swatch swatch--mid" aria-hidden /> Medium risk
        </li>
        <li>
          <span className="swatch swatch--high" aria-hidden /> High risk
        </li>
      </ul>
    </aside>
  );
}
