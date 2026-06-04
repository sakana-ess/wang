import streamlit as st
import openai
import os

# ------------------------------ 页面设置 ------------------------------
st.set_page_config(page_title="髓问 · 脊髓解剖推理导师", page_icon="🧠")
st.title("🧠 髓问：脊髓核团与传导束的苏格拉底式智能推理导师")

# ------------------------------ API Key 获取 ------------------------------
# 优先从 secrets 读取，否则从环境变量读取，最后允许手动输入
api_key = None
try:
    api_key = st.secrets["OPENAI_API_KEY"]
except:
    api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    api_key = st.sidebar.text_input("请输入 OpenAI API Key（以sk-开头）", type="password")

if not api_key:
    st.warning("请在左侧输入有效的 API Key 以开始使用。")
    st.stop()

openai.api_key = api_key

# ------------------------------ 加载知识库 ------------------------------
@st.cache_data
def load_knowledge():
    try:
        with open("spinal_knowledge.txt", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "脊髓知识库文件未找到，请确保 spinal_knowledge.txt 存在。"

knowledge_text = load_knowledge()

# ------------------------------ 模式选择与系统提示构建 ------------------------------
mode = st.sidebar.selectbox(
    "选择推理模式",
    ["苏格拉底追问导师", "侦探病例推理局", "如果·解剖反例推演"],
    help="切换不同 AI 教学风格"
)

# 共享的基础角色定义
base_role = f"""你是一位神经解剖学教授，专门讲授脊髓灰质分层、核团与白质传导束。你必须严格遵守以下知识库：
{knowledge_text}

你的所有回答必须基于该知识库，绝对不编造解剖事实。如果学生的问题不在知识库内，请诚实说明，并尝试用已知解剖知识类比引导。
"""

# 根据不同模式细化行为规则
if mode == "苏格拉底追问导师":
    system_prompt = base_role + """
【当前模式：苏格拉底追问导师】
你的教学方法如下：
1. 当学生提问某个结构（如“后角固有核和胶状质有何不同”），你绝不直接给定义。
2. 你先反问一个与该结构功能相关的临床问题，例如：“如果我们用针轻刺皮肤，痛觉进入脊髓后第一个抵达的灰质层是哪一层？”
3. 根据学生的回答，你再一层层追问，直到他们自己说出关键传导通路和核团关系。
4. 如果学生答错，给一个小反例，比如：“不对，假如损伤在那层，为什么温度觉还在？再想想。”
5. 最后用简练的知识总结收尾，并鼓励学生继续追问。
6. 始终保持温暖而严谨的语气，像一位耐心引导的导师。
"""
elif mode == "侦探病例推理局":
    system_prompt = base_role + """
【当前模式：侦探病例推理局】
你的角色是神经解剖学“案件主持人”：
1. 首先，你随机生成一个虚拟的脊髓损伤病例，提供明确的症状（如感觉缺失类型、瘫痪部位、反射变化），但绝不直接说出损伤的节段和结构名称。
2. 病例必须严格符合知识库中传导束和核团的功能，症状要合乎逻辑。
3. 然后，引导学生提问进行检查（如“我可以查他的膝腱反射吗？”），你根据损伤真实情况给出虚构的检查结果。
4. 当学生提出定位诊断（比如“我猜损伤在胸段，累及左侧薄束和右侧脊髓丘脑侧束”），你评判对错，并详细解释正确诊断的解剖依据，说明为什么该结构受损引起这些症状。
5. 如果学生定位错误，你明确指出选错的某个结构，并结合传导通路推理为什么该结构的症状不相符。
6. 请鼓励学生继续挑战下一个随机病例。
"""
else:  # "如果·解剖反例推演"
    system_prompt = base_role + """
【当前模式：如果·解剖反例推演】
你擅长引导学生思考“假如某个核团或传导束被选择性破坏，会发生什么”。
1. 学生可以提出一个假设，如“如果仅前角α运动神经元死亡而γ神经元完好，肌张力如何？”
2. 你基于知识库中的解剖连接，一步步推导出合理的临床表现，区分主动运动、肌张力、反射的变化。
3. 你也可以主动抛出反事实问题，让学生推理：“如果我们能单独阻断Rexed II层胶状质，痛觉会发生什么变化？”
4. 整个过程中，你始终强调解剖结构与功能的因果逻辑，帮助学生形成动态的三维神经环路思维。
5. 语气可以充满探究感，像科学讨论一样。
"""

# ------------------------------ 初始化对话历史 ------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
    # 初始欢迎语
    if mode == "苏格拉底追问导师":
        welcome = "你好，我是你的神经解剖导师。想问什么？不过我先提醒你，我可能不会直接告诉你答案，而是用问题引导你自己发现。试试看，比如问我后角胶状质和固有核的区别？"
    elif mode == "侦探病例推理局":
        welcome = "🔍 欢迎来到脊髓侦探社。我已经准备好一个匿名病例，你准备好开始推理了吗？你可以问我：“请给我第一个病例。”"
    else:
        welcome = "🧪 欢迎进入‘如果’解剖实验室。想象任何一个脊髓结构被选择性破坏，我们一起来推演结果。比如，你可以问：“如果Clarke柱在胸段完全坏死，但后索完好，会怎样？”"
    st.session_state.messages.append({"role": "assistant", "content": welcome})

# ------------------------------ 聊天界面显示 ------------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ------------------------------ 用户输入与 API 调用 ------------------------------
if prompt := st.chat_input("输入你的问题或推理..."):
    # 添加用户消息
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 调用 OpenAI API
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        try:
            # 构建消息列表（系统 + 历史 + 新问题）
            messages = [{"role": "system", "content": system_prompt}]
            messages += st.session_state.messages  # 包含最新的 user 消息

            # 流式调用，体验更佳
            response = openai.chat.completions.create(
                model="gpt-4o-mini",  # 可换成 gpt-4o 或 deepseek-chat
                messages=messages,
                temperature=0.7,
                stream=True,
            )
            for chunk in response:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    message_placeholder.markdown(full_response + "▌")
            message_placeholder.markdown(full_response)
        except Exception as e:
            full_response = f"❌ API 调用出错：{str(e)}"
            message_placeholder.error(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})

# ------------------------------ 侧边栏信息 ------------------------------
st.sidebar.markdown("---")
st.sidebar.info(
    "**《髓问》使用说明**\n\n"
    "1. 输入你的 OpenAI API Key（需有额度）。\n"
    "2. 切换三种推理模式，体验不同教学风格。\n"
    "3. 知识库已内置脊髓灰质、白质、核团全部核心内容。\n"
    "4. 推荐使用 `gpt-4o-mini`，成本极低，推理能力强。\n"
    "5. 若希望免费使用，可替换为 DeepSeek API，修改 base_url 即可。"
)
st.sidebar.markdown("**当前模式:** " + mode)