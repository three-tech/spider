#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
小红书会员管理模块
提供member_xhs表的CRUD操作接口
"""

import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from base.database import DatabaseManager
from base.logger import get_logger


class MemberXhsManager:
    """小红书会员管理器"""

    def __init__(self):
        """初始化管理器"""
        self.db = DatabaseManager()
        self.logger = get_logger(__name__)

    def add_member(self, user_name, xhs_id, tags=None):
        """添加小红书会员"""
        member_data = {
            'userName': user_name,
            'xhs_id': xhs_id,
            'tags': tags or ''
        }

        result = self.db.save_member_xhs(member_data)
        if result:
            self.logger.info(f"✅ 成功添加小红书会员: {user_name}")
        else:
            self.logger.info(f"ℹ️ 小红书会员已存在，已更新: {user_name}")

        return result

    def get_member_by_id(self, xhs_id):
        """根据小红书ID获取会员信息"""
        return self.db.get_member_xhs_by_id(xhs_id)

    def get_all_members(self):
        """获取所有小红书会员"""
        return self.db.get_all_member_xhs()

    def update_member_tags(self, xhs_id, tags):
        """更新会员标签"""
        return self.db.update_member_xhs_tags(xhs_id, tags)

    def delete_member(self, xhs_id):
        """删除会员"""
        return self.db.delete_member_xhs(xhs_id)

    def search_members_by_tag(self, tag):
        """根据标签搜索会员"""
        all_members = self.get_all_members()
        result = []

        for member in all_members:
            if member.tags and tag in member.tags:
                result.append(member)

        return result

    def add_tag_to_member(self, xhs_id, new_tag):
        """为会员添加新标签"""
        member = self.get_member_by_id(xhs_id)
        if not member:
            self.logger.warning(f"⚠️ 会员不存在: {xhs_id}")
            return False

        current_tags = member.tags or ''
        tags_list = [tag.strip() for tag in current_tags.split(',') if tag.strip()]

        if new_tag not in tags_list:
            tags_list.append(new_tag)
            new_tags = ','.join(tags_list)
            return self.update_member_tags(xhs_id, new_tags)
        else:
            self.logger.info(f"ℹ️ 标签已存在: {new_tag}")
            return True

    def remove_tag_from_member(self, xhs_id, tag_to_remove):
        """从会员中移除标签"""
        member = self.get_member_by_id(xhs_id)
        if not member:
            self.logger.warning(f"⚠️ 会员不存在: {xhs_id}")
            return False

        current_tags = member.tags or ''
        tags_list = [tag.strip() for tag in current_tags.split(',') if tag.strip()]

        if tag_to_remove in tags_list:
            tags_list.remove(tag_to_remove)
            new_tags = ','.join(tags_list)
            return self.update_member_tags(xhs_id, new_tags)
        else:
            self.logger.info(f"ℹ️ 标签不存在: {tag_to_remove}")
            return True
