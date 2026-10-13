export function PressureLegend() {
  return (
    <aside className="pressure-legend" aria-label="Chú thích áp lực">
      <p className="eyebrow">Áp lực trạm (pressure)</p>
      <p>
        Điểm áp lực ≈ 1 − khả năng còn cổng trống trong khung thời gian cố định.
        Cao hơn nghĩa là rủi ro thiếu cổng cao hơn — không phải lưu lượng đo
        trực tiếp.
      </p>
      <ul>
        <li>
          <span className="swatch swatch--low" aria-hidden /> Rủi ro thấp
        </li>
        <li>
          <span className="swatch swatch--mid" aria-hidden /> Rủi ro trung bình
        </li>
        <li>
          <span className="swatch swatch--high" aria-hidden /> Rủi ro cao
        </li>
      </ul>
    </aside>
  );
}
