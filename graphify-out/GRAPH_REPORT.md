# Graph Report - src  (2026-08-31)

## Corpus Check
- Corpus is ~45,469 words - fits in a single context window. You may not need a graph.

## Summary
- 1289 nodes · 2378 edges · 88 communities (41 shown, 47 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 260 edges (avg confidence: 0.56)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Phoebe Combat Logic
- Custom Team Loader
- Scene Base Framework
- Zani Combat Logic
- Aemeath Combat Logic
- BaseChar Core
- Cartethyia Combat Logic
- BaseTask Automation Core
- Char Factory & Type Init
- Roccia Combat Logic
- Farm Echo Task
- Linnai Combat Logic
- Brant Combat Logic
- Rover Combat Logic
- Domain Farming Task
- YOLO Detection Globals
- Mouse Reset Task
- Big Map Navigation
- Base Combat Resonance
- Nightmare Nest Task
- Camellya Combat Logic
- Carlotta Combat Logic
- Lucilla Combat Logic
- Combat Attack Helpers
- Skip/Dialog Feature Task
- Verina Combat Logic
- Liberation Skill Helpers
- AutoCombat Task Core
- Combat Cycle Helpers
- Zhezhi Combat Logic
- Daily Task
- Augusta Combat Logic
- Garden Task
- Changli Combat Logic
- Hiyuki Combat Logic
- Combat State Guards
- Dialog/Book Navigation
- Luhesi Combat Logic
- Revive & Recovery Handling
- Echo Skill Dispatch
- Douling Combat Logic
- Jinhsi Combat Logic
- Phrolova Combat Logic
- Rebecca Combat Logic
- Xigelika Combat Logic
- Cooldown/Resonance Checks
- Hotkey & Char Identity
- Concerto Ring Detection
- Text/Image Matching Utils
- YOLO Echo Navigation
- Landing & Cooldown State
- Encore Combat Logic
- ShoreKeeper Combat Logic
- World/Realm State Checks
- Cantarella Combat Logic
- Combat Loop & Healer Switch
- Default Combat Rotation
- Switch Priority Rules
- Lucy Combat Logic
- Diagnosis Task
- Merge Echo Task
- Tacet Field Farming
- YangYangSp Combat Logic
- Galbrena Combat Logic
- Xiangliyao Combat Logic
- Fast Travel Task
- Resonance Key Dispatch
- Danjin Combat Logic
- Qiuyuan Combat Logic
- Baizhi Combat Logic
- Calcharo Combat Logic
- Chixia Combat Logic
- Jianxin Combat Logic
- Jiyan Combat Logic
- Mortefi Combat Logic
- Phoebe State Enum
- Sanhua Combat Logic
- Taoqi Combat Logic
- Yinlin Combat Logic
- Youhu Combat Logic
- Yuanwu Combat Logic
- GUI Frontend Entry

## God Nodes (most connected - your core abstractions)
1. `BaseChar` - 149 edges
2. `BaseWWTask` - 99 edges
3. `BaseCombatTask` - 79 edges
4. `Phoebe` - 62 edges
5. `Zani` - 52 edges
6. `SwitchPriority` - 34 edges
7. `FarmEchoTask` - 33 edges
8. `CombatCheck` - 31 edges
9. `Rover` - 28 edges
10. `DailyTask` - 23 edges

## Surprising Connections (you probably didn't know these)
- `CombatCheck` --uses--> `Labels`  [INFERRED]
  combat/CombatCheck.py → Labels.py
- `BaseWWTask` --uses--> `Labels`  [INFERRED]
  task/BaseWWTask.py → Labels.py
- `GardenTask` --uses--> `Labels`  [INFERRED]
  task/GardenTask.py → Labels.py
- `MergeEchoTask` --uses--> `Labels`  [INFERRED]
  task/MergeEchoTask.py → Labels.py
- `CharType` --uses--> `AutoCombatTask`  [INFERRED]
  char/BaseChar.py → task/AutoCombatTask.py

## Import Cycles
- None detected.

## Communities (88 total, 47 thin omitted)

### Community 0 - "Phoebe Combat Logic"
Cohesion: 0.07
Nodes (19): Phoebe, 赞妮大招无 token 回切：不消耗菲比资源，立即交还赞妮。, 赞妮大招 phase2/3 落地即跑 insert 短轴。赞菲光：token 命中才进（starflash+定身+切回）；…, 切人前收尾（逐过程）：[非赞菲光补第 2 次 starflash] → 普攻到协奏 → 切人。 （E 定身已移到 _do_regular_rotation 的…, 赞妮大招插入：切入后立即 starflash 蓄力重击（图标亮直接打，不亮由充能段 左键凑图标——给赞妮回能量）→ 短按 E…, Insert 重击后的短按 E 定身；UI 检测未发键时补一次受控短按。, 落地等待：滞空时 wait_down，仍飞则限时点击辅助落地（点击仅为落地，不构成输出）。, 长按共鸣键 duration 秒（next_frame 等待）。形态进入与 recovery 共用。 (+11 more)

### Community 1 - "Custom Team Loader"
Cohesion: 0.10
Nodes (44): apply_team_char_classes(), Apply custom code only after the complete three-character team is known., clear_custom_char_cache(), clear_team_char_cache(), create_custom_team(), _default_team_manifest(), delete_custom_team(), export_custom_team() (+36 more)

### Community 2 - "Scene Base Framework"
Cohesion: 0.06
Nodes (13): BaseScene, Exception, WWScene, AutoLoginTask, TriggerTask, AutoPickTask, TriggerTask, ChangeEchoTask (+5 more)

### Community 3 - "Zani Combat Logic"
Cohesion: 0.10
Nodes (6): Enum, 处理非大招轮转。 赞菲光完成危机动作后直接尝试开大，赞菲奶按焰光阈值开大。, 第一、二阶段默认切人，由落地角色执行插入轴。, 等待条件成立、中断条件触发或超时。 条件成立返回 True，超时返回 False，中断返回 State.INTERRUPTED。, State, Zani

### Community 4 - "Aemeath Combat Logic"
Cohesion: 0.07
Nodes (7): Aemeath, Denia, Qingxiao, Suisui, Labels, Enum, str

### Community 5 - "BaseChar Core"
Cohesion: 0.05
Nodes (12): BaseChar, 使用F进行击破 若self.check_f_on_switch为False则不在切走前自动按F,须在逻辑中手动添加。…, Return whether an intro arrives with both teammates' timed buffs active., 是否在某些操作中跳过战斗状态检查。 Returns: bool: 如果跳过则返回 True。, 比较两个角色对象是否相同 (基于名称和索引)。, 角色基类，定义了游戏角色的通用属性和行为。 AI editing guide: - Character subclasses usually override…, 重置角色的战斗相关状态 (如入场技标记)。 BaseCombatTask calls this after loading the team. Do not…, 当战斗结束时, 角色可能需要执行的特定清理逻辑。 Args: chars (list[BaseChar]): 队伍中所有角色的列表。 (+4 more)

### Community 6 - "Cartethyia Combat Logic"
Cohesion: 0.10
Nodes (3): Cartethyia, setter, Ciaccona

### Community 7 - "BaseTask Automation Core"
Cohesion: 0.07
Nodes (6): BaseTask, BaseWWTask, setter, Determines the direction ('w', 'a', 's', 'd') closest to the screen center.…, Main function to load ONNX model, perform inference, draw bounding boxes, and…, Releases keys and mouse to stop character movement.

### Community 8 - "Char Factory & Type Init"
Cohesion: 0.11
Nodes (11): CharType, get_default_buff_time(), 初始化角色基础属性。 Args: task (BaseCombatTask): 所属的战斗任务对象。 index (int): 角色在队伍中的索引 (0,…, _apply_char_config(), _find_registered_char(), _get_buff_time(), get_char_by_pos(), _get_char_type() (+3 more)

### Community 9 - "Roccia Combat Logic"
Cohesion: 0.09
Nodes (3): Roccia, CombatCheck, setter

### Community 11 - "Linnai Combat Logic"
Cohesion: 0.12
Nodes (4): Linnai, 攒满回路后蓄力重击; 攒满即放, 放完接 perform_under_intro。 无论是否协奏入场都执行: Mornye…, 等待琳奈入场后的目标状态稳定，避免特效遮挡导致一帧误判。, Mornye

### Community 13 - "Rover Combat Logic"
Cohesion: 0.14
Nodes (4): 赞妮大招插入：E → R → Q → 切回赞妮。, 赞妮大招插队窗口：phase 2/3 且仍在 liberation 时跑 insert 短轴。, 非 Spectro 形态不执行 Insert，丢弃本次 token 后继续自身 routine。, Rover

### Community 14 - "Domain Farming Task"
Cohesion: 0.10
Nodes (6): DomainTask, 副本内死亡恢复：关闭弹窗 → 退出副本 → 传最近传送点回血。, 包装副本刷取循环：死亡恢复后自动从 F2 重新进入，并限制重试次数。, 刷本循环；返回 (是否整段正常结束, 剩余 must_use)。 第二项在死亡提前退出时仍会带上本局内已扣过的额度，供外层恢复循环继续传参。, ForgeryTask, SimulationTask

### Community 15 - "YOLO Detection Globals"
Cohesion: 0.11
Nodes (8): Globals, OnnxYolo8Detect, ndarray, Perform post-processing on the model's output., yolov ONNX Runtime inference dic_labels: {0: 'person', 1: 'bicycle'}, Resize and reshape images while maintaining aspect ratio by adding padding.…, OpenVinoYolo8Detect, ndarray

### Community 16 - "Mouse Reset Task"
Cohesion: 0.15
Nodes (5): MouseResetTask, TriggerTask, MultiAccountDailyTask, normalize_account_name(), Box

### Community 17 - "Big Map Navigation"
Cohesion: 0.14
Nodes (10): calculate_angle_clockwise(), Calculates angle (radians) from horizontal right to line (x1,y1)->(x2,y2).…, BigMap, create_circle_mask_with_hole(), create_color_mask(), FarmMapTask, mask_star(), Creates a binary circular mask with a rectangular hole in the center. The… (+2 more)

### Community 18 - "Base Combat Resonance"
Cohesion: 0.10
Nodes (10): BaseCombatTask, 发送按键并等待动画完成。 Args: key (str): 要发送的按键。 check_function (callable): 检查动画是否结束的函数，返回…, Translate a 16:9 HUD x-coordinate to the current screen width. The skill row…, 通过绕圈移动来尝试拾取声骸。 Args: circle_count (int, optional): 绕圈的次数。默认为 3。 Returns: bool:…, 初始化战斗任务。 Args: *args: 传递给父类的参数。 **kwargs: 传递给父类的关键字参数。, 获取共鸣技能的按键。 Returns: str: 共鸣技能的按键字符串。, 判断是否应该更新角色对象 (例如, 识别到新角色或角色类型变化)。 Args: the_char (BaseChar): 新的角色对象。 old_char…, 获取共鸣技能冷却UI区域的盒子对象。 Returns: Box: 盒子对象。 (+2 more)

### Community 19 - "Nightmare Nest Task"
Cohesion: 0.16
Nodes (3): convert_image_to_negative(), NestTarget, NightmareNestTask

### Community 22 - "Lucilla Combat Logic"
Cohesion: 0.15
Nodes (9): Lucilla, 变身后脉冲式重击 total_time 秒: 反复 mouse_down/sleep/mouse_up. 每拍重新 mouse_down, 某拍被打断,…, 长按共鸣技能键一段时间 (攒 1 格回路能量)。 长按期间用 check_combat=False: 攒能量在正常态, in_combat()…, 攒能量 -> 大招可用则放大招接输出. Returns: bool: 放出了大招(并已在 try_liberation 内切人)返回 True, 否则…, 攒 1 格回路能量: E 可用优先长按 E、否则蓄力重击., 大招就绪则放招(顺带先放声骸), 返回是否放出。 仅在大招可用(能量满且无CD)时才放招; 未就绪只返回 False, 由外层(perform_combat…, Lucilla 自动战斗: 回路充能型 + 大招变身型角色。 机制: 长按 E 或蓄力重击各攒 1 格回路能量, 攒满 3 格大招可用;…, 回路能量是否已满(解放图标高亮, 忽略CD)。 liberation_available() 把"能量满"和"无CD"绑在一起判断, 故用… (+1 more)

### Community 23 - "Combat Attack Helpers"
Cohesion: 0.14
Nodes (5): 尝试点击并释放共鸣技能。 Args: post_sleep (float, optional): 释放技能后的休眠时间。默认为 0。…, 检查战斗状态 (代理到 task.check_combat)。, 判断共鸣技能是否可用。 Args: current (float, optional): 可选的, 当前共鸣技能UI白色像素百分比。默认为 None。…, 持续进行普通攻击一段时间。 Args: duration (float): 持续时间 (秒)。 interval (float, optional):…, 执行一次重攻击。 Args: duration (float, optional): 重攻击按键按下的持续时间。默认为 0.6。

### Community 24 - "Skip/Dialog Feature Task"
Cohesion: 0.14
Nodes (5): convert_dialog_icon(), process_feature(), SkipBaseTask, AutoDialogTask, TriggerTask

### Community 25 - "Verina Combat Logic"
Cohesion: 0.16
Nodes (5): 3A -> 大招 -> E -> 声骸 -> (重击) -> 跳跃 -> 2A; 协奏满/超时则提前结束去切人。, 连招是否应提前结束去切人: 协奏满(攒够入场技) 或 在场超时。, 距上次重击是否已超过最小间隔(扣除冻结时间)。, Verina 自动战斗(辅助/治疗): 3A -> 大招 -> E -> 声骸 -> (重击) -> 跳跃 -> 2A; 协奏满或超时则立即切人。, Verina

### Community 27 - "Liberation Skill Helpers"
Cohesion: 0.13
Nodes (7): Any, 以指定间隔执行点击操作。 Args: interval (float, optional): 点击间隔。默认为 0.1。, 执行一次点击操作 (代理到 task.click)。, 发送共鸣解放按键。 Args: after_sleep (float, optional): 发送后的休眠时间。默认为 0。 interval (float,…, 尝试点击并释放共鸣解放。 Args: con_less_than (float, optional): 仅当协奏值小于此值时释放。默认为 -1 (不检查)。…, 添加冻结持续时间 (代理到 task.add_freeze_duration)。, 获取共鸣解放按键 (代理到 task.get_liberation_key)。

### Community 28 - "AutoCombat Task Core"
Cohesion: 0.22
Nodes (9): Elements, SwitchPriority, IntEnum, AutoCombatTask, TriggerTask, CharDeadException, CharRevivedException, NotInCombatException (+1 more)

### Community 29 - "Combat Cycle Helpers"
Cohesion: 0.14
Nodes (4): 切换到下一个角色 (代理到 task.switch_next_char)。 Args: post_action (callable, optional):…, 判断最左边的额外技能是否可用。 Args: current (float, optional): 可选的, 当前声骸技能UI白色像素百分比。默认为 None。…, 判断共鸣回路是否已充满/可用。 Returns: bool: 如果充满/可用则返回 True。, 判断共鸣解放是否可用。 Returns: bool: 如果可用则返回 True。

### Community 33 - "Garden Task"
Cohesion: 0.24
Nodes (3): 获取角色类名作为其名称。 Returns: str: 角色类名字符串。, GardenTask, At Garden Entrance, choose first blessing

### Community 36 - "Combat State Guards"
Cohesion: 0.18
Nodes (5): 抛出未在战斗状态的异常。 Args: message (str): 异常信息。 exception_type (Exception, optional):…, 切换到下一个最优角色。 Args: current_char (BaseChar): 当前角色对象。 post_action (callable,…, 休眠指定时间, 并在休眠前后检查战斗状态。 Args: timeout (float): 休眠的秒数。 check_combat (bool,…, 检查当前是否处于战斗状态, 如果不是则抛出异常。, 添加冻结持续时间。用于精确计算技能冷却等。 Args: start (float): 冻结开始时间。 duration (float, optional):…

### Community 39 - "Revive & Recovery Handling"
Cohesion: 0.18
Nodes (5): 关闭角色死亡弹窗。 优先点击弹窗按钮 (避免 ESC 注入偶发不生效)，依次尝试: cancel_button → btn_dialog_close →…, 角色死亡恢复：关闭弹窗 → 传最近传送点回血。, 搜索对应语言的无冠者/Crownless→探测打开地图→找最近传送点回血。 不再依赖已被移除的 go_to_tower。改用 F2…, 按 M 开图, 就近找传送点回血 (供 FarmEchoTask 在 boss 点使用)。, 在已打开的地图界面上, 找最近传送点并传送, 等回到大世界。

### Community 40 - "Echo Skill Dispatch"
Cohesion: 0.20
Nodes (4): 发送声骸技能按键。 Args: after_sleep (float, optional): 发送后的休眠时间。默认为 0。 interval (float,…, 尝试点击并释放声骸技能。 Args: duration (float, optional): 技能期望的持续按键时间 (用于持续型声骸)。默认为 0。…, 获取声骸技能按键 (代理到 task.get_echo_key)。, 判断声骸技能是否可用。 Args: current (float, optional): 可选的, 当前声骸技能UI白色像素百分比。默认为 None。…

### Community 46 - "Cooldown/Resonance Checks"
Cohesion: 0.20
Nodes (4): 检查指定名称的技能或动作是否可用 (通过颜色百分比和冷却时间判断)。 Args: name (str): 技能或动作的名称 (例如 'resonance',…, 检查共鸣技能是否在冷却中。 Returns: bool: 如果在冷却中则返回 True, 否则 False。, 检查指定UI区域是否处于冷却状态 (通过检测特定颜色的点和数字)。 Args: box_name (str): UI区域的名称 (例如…, 计算扣除冻结时间后经过的时间。 Args: start (float): 开始时间戳。 intro_motion_freeze (bool,…

### Community 47 - "Hotkey & Char Identity"
Cohesion: 0.20
Nodes (3): 获取共鸣解放技能的按键。 Returns: str: 共鸣解放技能的按键字符串。, 获取声骸技能的按键。 Returns: str: 声骸技能的按键字符串。, 加载或自动设置游戏内技能热键。 Args: force (bool, optional): 是否强制重新加载热键。默认为 False。

### Community 49 - "Concerto Ring Detection"
Cohesion: 0.22
Nodes (5): 在指定图像区域内计算特定颜色范围的能量环数量和状态。 Args: image (numpy.ndarray): 要分析的图像 (通常是协奏值UI区域的截图)。…, 检查当前角色的协奏值是否已满。 Returns: bool: 如果协奏值已满则返回 True, 否则 False。, 确保当前角色协奏值环的颜色索引已识别。 Returns: int: 协奏值环的颜色索引。, 获取协奏值能量环的UI区域盒子对象。 Returns: Box: 盒子对象。, 获取当前角色的协奏值百分比。 Returns: float: 协奏值百分比 (0.0 到 1.0)。

### Community 50 - "Text/Image Matching Utils"
Cohesion: 0.20
Nodes (6): convert_cd(), Strips a string to only keep the first part that matches the regex pattern.…, binarize_for_matching(), isolate_white_text_to_black(), Converts pixels in the near-white range (244-255) to black, and all others to…, Converts a colored image to a binary image based on a brightness threshold. The…

### Community 52 - "Landing & Cooldown State"
Cohesion: 0.22
Nodes (3): 判断角色是否已落地 (通过技能是否可用判断)。 Returns: bool: 如果已落地则返回 True。, 检查指定技能是否在冷却中 (代理到 task.has_cd)。 Args: box_name (str): 技能UI区域名称。 Returns: bool:…, 判断技能是否可用 (基于UI百分比和冷却状态)。 Args: percent (float): 技能UI白色像素百分比。 box_name (str):…

### Community 59 - "Default Combat Rotation"
Cohesion: 0.29
Nodes (3): 执行当前角色的主要战斗行动序列。 ``perform`` is called by AutoCombatTask when this character is…, 等待角色入场动画结束。 Args: time_out (float, optional): 等待超时时间 (秒)。默认为 1.2。 click (bool,…, 执行角色的标准战斗行动。 This default rotation is intentionally conservative: wait for…

## Knowledge Gaps
- **47 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `BaseChar` connect `BaseChar Core` to `Phoebe Combat Logic`, `Zani Combat Logic`, `Aemeath Combat Logic`, `Cartethyia Combat Logic`, `Char Factory & Type Init`, `Roccia Combat Logic`, `Linnai Combat Logic`, `Brant Combat Logic`, `Rover Combat Logic`, `Base Combat Resonance`, `Camellya Combat Logic`, `Carlotta Combat Logic`, `Lucilla Combat Logic`, `Combat Attack Helpers`, `Verina Combat Logic`, `Liberation Skill Helpers`, `AutoCombat Task Core`, `Combat Cycle Helpers`, `Zhezhi Combat Logic`, `Augusta Combat Logic`, `Garden Task`, `Changli Combat Logic`, `Hiyuki Combat Logic`, `Luhesi Combat Logic`, `Echo Skill Dispatch`, `Douling Combat Logic`, `Jinhsi Combat Logic`, `Phrolova Combat Logic`, `Rebecca Combat Logic`, `Xigelika Combat Logic`, `Landing & Cooldown State`, `Encore Combat Logic`, `ShoreKeeper Combat Logic`, `Cantarella Combat Logic`, `Combat Loop & Healer Switch`, `Default Combat Rotation`, `Switch Priority Rules`, `Lucy Combat Logic`, `YangYangSp Combat Logic`, `Galbrena Combat Logic`, `Xiangliyao Combat Logic`, `Resonance Key Dispatch`, `Danjin Combat Logic`, `Qiuyuan Combat Logic`, `Baizhi Combat Logic`, `Calcharo Combat Logic`, `Chixia Combat Logic`, `Jianxin Combat Logic`, `Jiyan Combat Logic`, `Mortefi Combat Logic`, `Phoebe State Enum`, `Sanhua Combat Logic`, `Taoqi Combat Logic`, `Yinlin Combat Logic`, `Youhu Combat Logic`, `Yuanwu Combat Logic`?**
  _High betweenness centrality (0.560) - this node is a cross-community bridge._
- **Why does `BaseCombatTask` connect `Base Combat Resonance` to `Scene Base Framework`, `BaseChar Core`, `Roccia Combat Logic`, `Farm Echo Task`, `Domain Farming Task`, `Mouse Reset Task`, `Big Map Navigation`, `Nightmare Nest Task`, `AutoCombat Task Core`, `Daily Task`, `Combat State Guards`, `Revive & Recovery Handling`, `Cooldown/Resonance Checks`, `Hotkey & Char Identity`, `Switch Target Selection`, `Concerto Ring Detection`, `Text/Image Matching Utils`, `ShoreKeeper Combat Logic`, `Combat Loop & Healer Switch`, `Diagnosis Task`, `Tacet Field Farming`?**
  _High betweenness centrality (0.330) - this node is a cross-community bridge._
- **Why does `SwitchPriority` connect `AutoCombat Task Core` to `Phoebe Combat Logic`, `Zani Combat Logic`, `Aemeath Combat Logic`, `Cartethyia Combat Logic`, `Char Factory & Type Init`, `Linnai Combat Logic`, `Brant Combat Logic`, `Base Combat Resonance`, `Camellya Combat Logic`, `Carlotta Combat Logic`, `Lucilla Combat Logic`, `Verina Combat Logic`, `Zhezhi Combat Logic`, `Changli Combat Logic`, `Hiyuki Combat Logic`, `Luhesi Combat Logic`, `Douling Combat Logic`, `Jinhsi Combat Logic`, `Phrolova Combat Logic`, `Encore Combat Logic`, `ShoreKeeper Combat Logic`, `Cantarella Combat Logic`, `Lucy Combat Logic`, `Phoebe State Enum`?**
  _High betweenness centrality (0.157) - this node is a cross-community bridge._
- **Are the 58 inferred relationships involving `BaseChar` (e.g. with `Aemeath` and `Augusta`) actually correct?**
  _`BaseChar` has 58 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `BaseWWTask` (e.g. with `CombatCheck` and `AutoLoginTask`) actually correct?**
  _`BaseWWTask` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `BaseCombatTask` (e.g. with `AutoCombatTask` and `BaseChar`) actually correct?**
  _`BaseCombatTask` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `Phoebe` (e.g. with `Ciaccona` and `BaseChar`) actually correct?**
  _`Phoebe` has 9 INFERRED edges - model-reasoned connections that need verification._