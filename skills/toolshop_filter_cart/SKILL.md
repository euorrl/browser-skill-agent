---
name: toolshop_filter_cart
description: 在 Toolshop 测试商城搜索商品、按分类筛选和价格升序排序，并将指定数量的商品加入购物车。当用户要求操作该测试商城或验证筛选与购物车流程时使用；不适用于其他商城或结账支付。
params: [keyword, category, product_name, quantity]
start: "https://practicesoftwaretesting.com/"
goal: "在 Toolshop 练习商城完成搜索、分类筛选、价格排序，找到 {{product_name}}，设置数量 {{quantity}} 并加入购物车；实际进入购物车读取对应商品行，报告商品名称、数量、价格和总计。只操作练习购物车，不登录、不结账。"
actions:
- title: 等待首页语言菜单
  tool: wait_for
  args:
    target:
      role: button
      name: Select language
    timeout: 30
- title: 展开语言菜单
  tool: click
  args:
    target:
      role: button
      name: Select language
- title: 切换英语
  tool: click
  args:
    target:
      role: menuitem
      name: EN
- title: 等待分类加载
  tool: wait_for
  args:
    target:
      role: checkbox
      name: '{{category}}'
    timeout: 30
- title: 要求购物车初始为空
  tool: wait_for
  args:
    target:
      role: link
      name: cart
    state: hidden
    timeout: 1
- title: 输入搜索词
  tool: fill
  args:
    target:
      role: textbox
      name: Search
    value_ref: keyword
- title: 搜索并等待返回
  tool: click
  args:
    target:
      role: button
      name: Search
    wait_response: https://api.practicesoftwaretesting.com/products/search
    wait_after:
      target: &id001
        role: heading
        name: '{{product_name}}'
      timeout: 30
- title: 分类筛选并等待返回
  tool: set_checked
  args:
    target:
      role: checkbox
      name: '{{category}}'
    checked: true
    wait_response: https://api.practicesoftwaretesting.com/products
    wait_after:
      target: *id001
      timeout: 30
- title: 按价格升序排序
  tool: select
  args:
    target:
      role: combobox
      name: sort
    label: Price (Low - High)
    wait_response: https://api.practicesoftwaretesting.com/products
    wait_after:
      target: *id001
      timeout: 30
- title: 进入指定商品详情
  tool: click
  args:
    target: *id001
    wait_after:
      url: '**/product/**'
      timeout: 30
- title: 填写购买数量
  tool: fill
  args:
    target:
      role: spinbutton
      name: Quantity
    value_ref: quantity
    wait_after:
      target:
        role: spinbutton
        name: Quantity
      state: value
      value: '{{quantity}}'
- title: 加入购物车并等待提示
  tool: click
  args:
    target:
      role: button
      name: Add to cart
    wait_after:
      target:
        text: Product added to shopping cart.
      timeout: 30
- title: 进入购物车
  tool: click
  args:
    target:
      role: link
      name: cart
    wait_after:
      url: '**/checkout'
      timeout: 30
- title: 等待购物车数量更新
  tool: wait_for
  args:
    target:
      role: spinbutton
      name: Quantity for {{product_name}}
    state: value
    value: '{{quantity}}'
    timeout: 30
- title: 购物车商品与金额
  tool: read
  args:
    target:
      role: table
    kind: text
- title: 实际商品数量
  tool: read
  args:
    target:
      role: spinbutton
      name: Quantity for {{product_name}}
    kind: value
---

## 默认脚本模式

默认按 actions 顺序执行，输出购物车表格和实际数量，不生成模型总结。要求商品位于筛选结果当前页，且可加入购物车；不自动翻页或替换商品。网页结构、语言菜单名称或接口改变时会停止，需要更新步骤或使用 --llm。


## 使用范围与输入

复用同一套搜索、筛选和购物车方法处理不同商品。关键词、分类、商品名称及数量由调用方提供，不能自行替换；数量应为正整数。本 Skill 的排序策略为价格升序。

| 参数 | 含义 |
| --- | --- |
| keyword | 商品搜索关键词 |
| category | 页面中分类复选框的准确名称 |
| product_name | 要加入购物车的完整商品名称 |
| quantity | 要加入的商品数量 |

## 任务边界

这是公开在线的自动化练习商城。只执行指定商品的搜索、筛选和加入购物车，不注册、不登录、不填写个人信息、不结账或支付。
本任务预期该站点的购物车初始为空；如果发现已有购物车项目，使用 blocked 结束，避免混入已有商品。
运行后保留练习购物车内容。再次演示前请手动清空购物车，或改用新的浏览器用户目录。

## 执行方法

1. 等待首页可操作；若界面不是英文，通过语言菜单切换为英语。确认购物车初始为空。
2. 搜索指定关键词，勾选指定分类，并选择价格升序。每次异步更新后等待相应结果，不把旧列表当作新结果。
3. 在结果中找到指定商品并进入详情。商品不存在或缺货时停止，不选择替代商品。
4. 将数量设置为指定值并读取确认，然后加入购物车。等待成功反馈；反馈超时先重新观察，不能直接重复添加。
5. 进入购物车，读取指定商品行的名称、数量、单价、小计和购物车总计，再汇总结果。

以上是任务方法，不是必须机械重放的点击顺序；已经满足的页面状态可以直接复用。

## 动态页面与组件

- 首屏可能只有导航或加载占位。优先 wait_for 等待 Search 输入框或商品标题出现，等待成功后再操作。
- 语言选择属于自定义菜单：click 展开后重新观察，选择实际显示的英语选项。不要对它调用 select。
- 商品排序是原生 select，可先 read(kind=options) 读取选项，再使用 select(label=实际选项文字)。
- 搜索框和按钮均叫 Search，应通过 textbox/button 角色区分。输入使用 value_ref=keyword。
- 分类通过 checkbox 的准确名称选择，不要勾选名字相似的父分类。通过 set_checked 设置为 true，避免反复点击导致取消。
- 排序和筛选会异步刷新结果。需要时 wait_for 等待商品标题，或等待观察中真实出现的加载提示消失；不要猜测加载器的名称。
- 目标有多个匹配时先 locate，查看候选并结合容器或实际返回的唯一标识定位，不猜测 nth。readiness 仅代表短时页面稳定，不能代替筛选结果就绪。
- 进入商品详情时可在点击中附带 wait_after(url="**/product/**")；进入购物车可等待 url="**/checkout"。加入购物车后可等待实际出现的“Product added to shopping cart.”提示；等待失败时先看购物车数量，不重复添加。
- 列表中商品链接通常包含名称、价格等多段文字。可以点击准确的商品 heading，或限定包含该商品名称的链接。不要依赖动态商品 ID 或固定 CSS。
- 输入数量时用 value_ref=quantity。若只有增减按钮，可根据当前数量逐次调整，不盲目增加指定次数。
- 商品详情和购物车数量都要读取实际值。最终截图不是本任务的输入，所有判断基于当前文字与 read 结果。
- 购物车入口可能位于导航中，名称随数量变化；以观察中的实际名称为准。表格行可用 role=row 加 has_text={{product_name}} 定位。
- 每个新动作前阅读当前状态和近期动作，已完成的搜索、语言设置等不必重做。最多 30 轮，保留足够轮数进入购物车。
- 若网络异常、缺货、字段不可编辑或目标不存在，如实说明阻塞原因，不编造价格或购物车内容。

## 最终结果

finish.message 用中文列出：搜索词、分类和排序方式；实际商品名；购物车中的数量、单价、商品小计及购物车总计；当前购物车 URL。没有读到的金额不得自行补写。只有购物车实际内容与任务相符才报告 succeeded。
