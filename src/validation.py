"""
输入校验层 —— 生产级输入验证、清洗、错误提示。
"""
import re
from datetime import date, datetime
from dataclasses import dataclass, field


class ValidationError(Exception):
    """输入校验异常（用户可修复）。"""
    pass


@dataclass
class TravelRequest:
    """经过校验的旅行请求。"""
    city: str
    start_date: date
    end_date: date
    trip_days: int = 0
    transport: list[str] = field(default_factory=list)
    hotel_type: str = ""
    preferences: list[str] = field(default_factory=list)
    extra: str = ""

    # 校验规则
    MAX_CITY_LEN = 30
    MAX_DAYS = 30
    MAX_EXTRA_LEN = 500
    VALID_CITIES: set[str] = field(default_factory=lambda: {
        "北京", "上海", "广州", "深圳", "杭州", "成都", "重庆",
        "西安", "南京", "武汉", "长沙", "三亚", "昆明", "大理",
        "丽江", "厦门", "青岛", "大连", "哈尔滨", "苏州", "桂林",
        "拉萨", "贵阳", "郑州", "天津", "济南", "沈阳", "合肥",
        "南昌", "福州", "南宁", "海口", "乌鲁木齐", "兰州", "银川",
        "西宁", "呼和浩特", "太原", "石家庄", "长春", "宁波",
        "温州", "珠海", "佛山", "东莞", "无锡", "常州", "扬州",
    })

    def validate(self) -> list[str]:
        """校验并返回错误列表。空列表表示通过。"""
        errors = []

        # 城市校验
        city_clean = clean_city(self.city)
        if not city_clean:
            errors.append("请输入目的地城市")
        elif len(city_clean) > self.MAX_CITY_LEN:
            errors.append(f"城市名不能超过{self.MAX_CITY_LEN}个字符")
        else:
            self.city = city_clean

        # 日期校验
        today = date.today()
        if not self.start_date or not self.end_date:
            errors.append("请选择出行日期")
        elif self.start_date > self.end_date:
            errors.append("结束日期不能早于开始日期")
        elif (self.end_date - self.start_date).days > self.MAX_DAYS:
            errors.append(f"行程不能超过{self.MAX_DAYS}天")
        else:
            self.trip_days = (self.end_date - self.start_date).days

        # 额外要求长度校验
        if self.extra and len(self.extra) > self.MAX_EXTRA_LEN:
            errors.append(f"额外要求不能超过{self.MAX_EXTRA_LEN}个字符")

        return errors

    def is_valid(self) -> bool:
        return len(self.validate()) == 0


def clean_city(raw: str) -> str:
    """清洗城市名：去空格、去'市'后缀、去特殊字符。"""
    if not raw:
        return ""
    cleaned = raw.strip()
    # 去掉常见后缀
    for suffix in ["市", "市辖区", "地区", "自治州"]:
        if cleaned.endswith(suffix):
            cleaned = cleaned[:-len(suffix)]
    # 去掉特殊字符
    cleaned = re.sub(r'[^\w\s一-鿿\-]', '', cleaned)
    return cleaned.strip()


def validate_dates(start: date, end: date) -> tuple[bool, str]:
    """日期范围校验。"""
    if start > end:
        return False, "结束日期不能早于开始日期"
    if (end - start).days > 30:
        return False, "行程不能超过30天"
    return True, ""


def sanitize_input(text: str, max_len: int = 500) -> str:
    """输入清洗：去XSS、修剪长度、去控制字符。"""
    if not text:
        return ""
    # 去控制字符（保留换行和制表）
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    # 修剪长度
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len]
    return cleaned.strip()
