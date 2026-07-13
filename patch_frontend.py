"""
修改前端 index.html：将 4 个套餐卡片缩减为 2 个（免费版 + 专业版）
"""
import re

def patch(html):
    # 1. CSS plan-tag styles - dark theme: remove basic/pro/enterprise, add paid
    html = re.sub(
        r'\[data-theme="dark"\] \.plan-tag\.basic \{[^}]+\}\s*\n\s*\[data-theme="dark"\] \.plan-tag\.pro \{[^}]+\}\s*\n\s*\[data-theme="dark"\] \.plan-tag\.enterprise \{[^}]+\}',
        '[data-theme="dark"] .plan-tag.paid { background: rgba(245,158,11,0.15); color: #fbbf24; }',
        html
    )

    # 2. CSS plan-tag styles - light theme: remove basic/pro/enterprise, add paid
    html = re.sub(
        r'\.plan-tag\.basic \{[^}]+\}\s*\n\s*\.plan-tag\.pro \{[^}]+\}\s*\n\s*\.plan-tag\.enterprise \{[^}]+\}',
        '.plan-tag.paid { background: #fffbeb; color: #d97706; }',
        html
    )

    # 3. planLabel function
    html = html.replace(
        "function planLabel(p) { return { free: '免费版', basic: '基础版', pro: '专业版', enterprise: '企业版' }[p] || '免费版'; }",
        "function planLabel(p) { return { free: '免费版', paid: '专业版' }[p] || '免费版'; }"
    )

    # 4. planOrder function
    html = html.replace(
        "function planOrder(p) { return { free: 0, basic: 1, pro: 2, enterprise: 3 }[p] || 0; }",
        "function planOrder(p) { return { free: 0, paid: 1 }[p] || 0; }"
    )

    # 5. Replace plan cards section (4 cards -> 2 cards)
    old_cards = '''              <div class="plan-cards">
                <div class="plan-card" :class="{current: tenantInfo.plan==='free'}">
                  <div class="plan-name">免费版</div>
                  <div class="plan-price"><span class="price-amount">¥0</span> / 月</div>
                  <ul class="plan-features">
                    <li>100 条消息/天</li>
                    <li>1 个 TG 账号</li>
                    <li>3 条映射规则</li>
                    <li>2 个钉钉 Bot</li>
                    <li>1 名团队成员</li>
                  </ul>
                  <el-button v-if="tenantInfo.plan==='free'" disabled style="margin-top:16px;width:100%">当前套餐</el-button>
                  <el-button v-else type="info" plain style="margin-top:16px;width:100%" @click="changePlan('free')">降到此套餐</el-button>
                </div>
                <div class="plan-card" :class="{current: tenantInfo.plan==='basic'}">
                  <div class="plan-name">基础版</div>
                  <div class="plan-price"><span class="price-amount">¥99</span> / 月</div>
                  <ul class="plan-features">
                    <li>1,000 条消息/天</li>
                    <li>2 个 TG 账号</li>
                    <li>10 条映射规则</li>
                    <li>5 个钉钉 Bot</li>
                    <li>5 名团队成员</li>
                  </ul>
                  <el-button v-if="tenantInfo.plan==='basic'" disabled style="margin-top:16px;width:100%">当前套餐</el-button>
                  <el-button v-else type="primary" plain style="margin-top:16px;width:100%" @click="changePlan('basic')">
                    {{ planOrder(tenantInfo.plan) < 2 ? '升级到' : '降到' }}此套餐
                  </el-button>
                </div>
                <div class="plan-card recommended" :class="{current: tenantInfo.plan==='pro'}">
                  <div class="plan-name" style="color:#d97706">专业版 ⭐</div>
                  <div class="plan-price"><span class="price-amount">¥299</span> / 月</div>
                  <ul class="plan-features">
                    <li>10,000 条消息/天</li>
                    <li>5 个 TG 账号</li>
                    <li>50 条映射规则</li>
                    <li>20 个钉钉 Bot</li>
                    <li>20 名团队成员</li>
                  </ul>
                  <el-button v-if="tenantInfo.plan==='pro'" disabled style="margin-top:16px;width:100%">当前套餐</el-button>
                  <el-button v-else type="warning" style="margin-top:16px;width:100%" @click="changePlan('pro')">
                    {{ planOrder(tenantInfo.plan) < 3 ? '升级到' : '降到' }}此套餐
                  </el-button>
                </div>
                <div class="plan-card" :class="{current: tenantInfo.plan==='enterprise'}">
                  <div class="plan-name" style="color:#059669">企业版 🏢</div>
                  <div class="plan-price"><span class="price-amount">¥999</span> / 月</div>
                  <ul class="plan-features">
                    <li>100,000 条消息/天</li>
                    <li>20 个 TG 账号</li>
                    <li>500 条映射规则</li>
                    <li>100 个钉钉 Bot</li>
                    <li>100 名团队成员</li>
                  </ul>
                  <el-button v-if="tenantInfo.plan==='enterprise'" disabled style="margin-top:16px;width:100%">当前套餐</el-button>
                  <el-button v-else type="success" style="margin-top:16px;width:100%" @click="changePlan('enterprise')">升级到此套餐</el-button>
                </div>
              </div>'''

    new_cards = '''              <div class="plan-cards" style="max-width:700px;margin:0 auto">
                <div class="plan-card" :class="{current: tenantInfo.plan==='free'}">
                  <div class="plan-name">免费版</div>
                  <div class="plan-price"><span class="price-amount">¥0</span> / 月</div>
                  <ul class="plan-features">
                    <li>100 条消息/天</li>
                    <li>1 个 TG 账号</li>
                    <li>3 条映射规则</li>
                    <li>2 个钉钉 Bot</li>
                    <li>1 名团队成员</li>
                  </ul>
                  <el-button v-if="tenantInfo.plan==='free'" disabled style="margin-top:16px;width:100%">当前套餐</el-button>
                  <el-button v-else type="info" plain style="margin-top:16px;width:100%" @click="changePlan('free')">降到此套餐</el-button>
                </div>
                <div class="plan-card recommended" :class="{current: tenantInfo.plan==='paid'}">
                  <div class="plan-name" style="color:#d97706">专业版 ⭐</div>
                  <div class="plan-price"><span class="price-amount">¥99</span> / 月</div>
                  <ul class="plan-features">
                    <li>消息无限制</li>
                    <li>TG 账号无限制</li>
                    <li>映射规则无限制</li>
                    <li>钉钉 Bot 无限制</li>
                    <li>团队成员无限制</li>
                  </ul>
                  <el-button v-if="tenantInfo.plan==='paid'" disabled style="margin-top:16px;width:100%">当前套餐</el-button>
                  <el-button v-else type="warning" style="margin-top:16px;width:100%" @click="changePlan('paid')">升级到此套餐</el-button>
                </div>
              </div>'''

    html = html.replace(old_cards, new_cards)

    # 6. Admin plan dropdown: replace 4 options with 2
    html = html.replace(
        '''<el-dropdown-item command="free" :disabled="row.plan==='free'">免费版</el-dropdown-item>
                          <el-dropdown-item command="basic" :disabled="row.plan==='basic'">基础版</el-dropdown-item>
                          <el-dropdown-item command="pro" :disabled="row.plan==='pro'">专业版</el-dropdown-item>
                          <el-dropdown-item command="enterprise" :disabled="row.plan==='enterprise'">企业版</el-dropdown-item>''',
        '''<el-dropdown-item command="free" :disabled="row.plan==='free'">免费版</el-dropdown-item>
                          <el-dropdown-item command="paid" :disabled="row.plan==='paid'">专业版</el-dropdown-item>'''
    )

    return html


if __name__ == "__main__":
    import sys
    path = sys.argv[1]
    with open(path, 'r') as f:
        html = f.read()
    patched = patch(html)
    with open(path, 'w') as f:
        f.write(patched)
    print(f"Patched {path}")
