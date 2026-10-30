"""Synthetic paper renderer. The OCR worker never imports this module."""

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

KINDS = {
    "employment_contract": (
        "HỢP ĐỒNG LAO ĐỘNG",
        {
            "contract_number": ("Số hợp đồng", "SYN-HD-{number:03d}"),
            "contract_type": ("Loại hợp đồng", "Có thời hạn 12 tháng"),
            "signed_date": ("Ngày ký", "2026-10-01"),
            "effective_date": ("Ngày hiệu lực", "2026-11-01"),
        },
    ),
    "degree": (
        "BẰNG TỐT NGHIỆP",
        {
            "degree_name": ("Tên bằng", "Cử nhân điều dưỡng"),
            "major": ("Chuyên ngành", "Điều dưỡng"),
            "issuer": ("Cơ sở cấp", "Trường đào tạo giả lập"),
            "issue_date": ("Ngày cấp", "2024-06-15"),
        },
    ),
    "practice_certificate": (
        "CHỨNG CHỈ HÀNH NGHỀ",
        {
            "certificate_number": ("Số chứng chỉ", "SYN-CCHN-{number:03d}"),
            "certificate_type": ("Loại chứng chỉ", "Điều dưỡng viên"),
            "issue_date": ("Ngày cấp", "2025-03-20"),
            "issuer": ("Cơ quan cấp", "Đơn vị cấp giả lập"),
        },
    ),
    "unknown": ("PHIẾU GHI CHÚ", {}),
}


def font(size, bold=False):
    names = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    path = next((name for name in names if Path(name).exists()), None)
    return ImageFont.truetype(path, size) if path else ImageFont.load_default(size=size)


def values(code, number):
    return {key: value.format(number=number) for key, (_, value) in KINDS[code][1].items()}


def render(code, employee_code, employee_name, page=1, page_count=1, family=0, spread_fields=False):
    number = int(employee_code.rsplit("-", 1)[-1])
    title, fields = KINDS[code]
    image = Image.new("RGB", (1240, 1754), "white")
    draw = ImageDraw.Draw(image)
    left = 90 if family % 2 == 0 else 120
    draw.text((left, 70), "DOCENTRA / HỒ SƠ GIẢ LẬP", font=font(25, True), fill="#24645b")
    draw.line((left, 125, 1150, 125), fill="#b3c9c3", width=3)
    draw.text((left, 180), title, font=font(43, True), fill="#152f2c")
    draw.text((left, 285), f"Mã nhân viên: {employee_code}", font=font(32), fill="black")
    draw.text((left, 345), f"Họ và tên: {employee_name}", font=font(32), fill="black")
    if page == 1 or spread_fields:
        y = 480
        for index, (key, (label, _)) in enumerate(fields.items()):
            if spread_fields and index % page_count != page - 1:
                continue
            draw.text((left, y), f"{label}: {values(code, number)[key]}", font=font(32), fill="black")
            y += 100
    else:
        draw.text((left, 500), "Nội dung bổ sung của tài liệu giả lập.", font=font(32), fill="black")
        draw.text((left, 585), "Trang này được lưu cùng tài liệu và giữ đúng thứ tự.", font=font(28), fill="black")
    draw.text((left, 1160), "Tài liệu này chỉ dùng để thử nghiệm quy trình số hóa.", font=font(29), fill="#555555")
    draw.text((left, 1230), "Không sử dụng để ra quyết định về nhân sự.", font=font(29), fill="#555555")
    draw.line((left, 1540, 1150, 1540), fill="#b3c9c3", width=2)
    draw.text((left, 1580), "DỮ LIỆU GIẢ LẬP / KHÔNG CÓ GIÁ TRỊ PHÁP LÝ", font=font(23, True), fill="#24645b")
    draw.text((left, 1640), f"Trang {page}/{page_count}", font=font(24), fill="#555555")
    output = BytesIO()
    image.save(output, "PNG")
    return output.getvalue()
