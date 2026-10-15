export function PressureLegend() {
  return (
    <aside className="pressure-legend" aria-label="Chú thích áp lực">
      <p className="eyebrow">NGUY CƠ THIẾU CHỖ</p>
      <p>
        Màu đỏ nghĩa là khả năng còn cổng thấp hơn tại giờ dự báo. Đây là dự báo
        còn chỗ, không phải số xe đang xếp hàng.
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
