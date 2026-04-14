"""
Agent Handoffs Example - 代理交接示例

展示 PraisonAI 风格的代理交接功能
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from code_gen.agents import Agent, AgentRole
from code_gen.agents.handoff import HandoffManager, HandoffConfig, create_handoff


async def example_1_basic_handoff():
    """示例1: 基础代理交接"""
    print("\n" + "="*60)
    print("示例1: 基础代理交接（客服场景）")
    print("="*60 + "\n")
    
    # 创建专业代理（这些都是自定义的 Agent 实例）
    billing_agent = Agent(
        name="BillingExpert",
        role=AgentRole.ASSISTANT,
        goal="处理账单相关问题",
        backstory="账单处理专家，精通退款、发票、付款问题"
    )
    
    refund_agent = Agent(
        name="RefundExpert", 
        role=AgentRole.ASSISTANT,
        goal="处理退款请求",
        backstory="退款专家，了解所有退款政策和流程"
    )
    
    technical_agent = Agent(
        name="TechSupport",
        role=AgentRole.ASSISTANT,
        goal="解决技术问题",
        backstory="技术支持专家，解决软件故障和技术问题"
    )
    
    # 创建分诊代理（主入口）
    triage_agent = Agent(
        name="Triage",
        role=AgentRole.ASSISTANT,
        goal="将客户问题路由给正确的专家",
        backstory="客服分诊专家，能够快速识别问题类型"
    )
    
    # 创建交接管理器
    handoff_manager = HandoffManager(Path("."))
    
    # 为分诊代理配置交接能力
    handoff_configs = [
        create_handoff(
            agent=billing_agent,
            name="transfer_to_billing",
            description="将账单相关问题转给账单专家（如发票、付款、费用问题）"
        ),
        create_handoff(
            agent=refund_agent,
            name="transfer_to_refund",
            description="将退款请求转给退款专家"
        ),
        create_handoff(
            agent=technical_agent,
            name="transfer_to_technical",
            description="将技术问题转给技术支持（如软件故障、使用问题）"
        )
    ]
    
    # 注册交接工具
    registration = handoff_manager.register_handoffs(triage_agent, handoff_configs)
    
    print(f"✅ 已为 {triage_agent.name} 配置交接能力")
    print(f"   可交接给: {[c.target_agent.name for c in handoff_configs]}")
    print(f"\n交接工具列表:")
    for tool in registration["tools"]:
        print(f"   - {tool['function']['name']}: {tool['function']['description']}")
    
    # 模拟交接
    context = {
        "history": [
            {"role": "user", "content": "我需要申请退款"},
            {"role": "assistant", "content": "我来帮您处理退款申请"}
        ]
    }
    
    result = await handoff_manager.execute_handoff(
        from_agent=triage_agent,
        to_agent=refund_agent,
        message="客户需要申请订单 #12345 的退款",
        context=context,
        config=handoff_configs[1]
    )
    
    print(f"\n交接结果:")
    print(f"   成功: {result['success']}")
    print(f"   从: {result['from']}")
    print(f"   到: {result['to']}")
    print(f"\n交接提示词预览:")
    print(f"   {result['handoff_prompt'][:200]}...")


async def example_2_handoff_with_callback():
    """示例2: 带回调的交接"""
    print("\n" + "="*60)
    print("示例2: 带回调的交接")
    print("="*60 + "\n")
    
    # 创建代理
    junior_agent = Agent(
        name="JuniorSupport",
        role=AgentRole.ASSISTANT,
        goal="处理基础客服问题",
        backstory="初级客服，处理简单问题"
    )
    
    senior_agent = Agent(
        name="SeniorManager",
        role=AgentRole.ASSISTANT,
        goal="处理复杂和升级问题",
        backstory="高级经理，处理复杂问题和投诉"
    )
    
    # 定义回调函数
    def log_handoff(from_agent: str, to_agent: str, context: dict) -> bool:
        """记录交接日志，并决定是否允许交接"""
        print(f"   📝 交接日志: {from_agent} → {to_agent}")
        
        # 可以在这里添加权限检查
        # 例如：只有特定问题才能升级给高级经理
        if "urgent" in str(context).lower():
            print(f"   ✅ 允许交接（紧急问题）")
            return True
        else:
            print(f"   ✅ 允许交接（普通问题）")
            return True
    
    # 创建带回调的交接配置
    escalation_config = create_handoff(
        agent=senior_agent,
        name="escalate_to_manager",
        description="将复杂问题升级给高级经理",
        callback=log_handoff
    )
    
    # 创建管理器并执行交接
    handoff_manager = HandoffManager(Path("."))
    
    context = {"issue_type": "urgent", "customer_tier": "premium"}
    
    result = await handoff_manager.execute_handoff(
        from_agent=junior_agent,
        to_agent=senior_agent,
        message="客户投诉账单错误，要求立即处理",
        context=context,
        config=escalation_config
    )
    
    print(f"\n交接完成!")


async def example_3_handoff_history():
    """示例3: 查看交接历史"""
    print("\n" + "="*60)
    print("示例3: 交接历史追踪")
    print("="*60 + "\n")
    
    # 创建多个代理
    agents = {
        "triage": Agent(name="Triage", role=AgentRole.ASSISTANT, goal="分诊", backstory="分诊员"),
        "billing": Agent(name="Billing", role=AgentRole.ASSISTANT, goal="账单", backstory="账单专家"),
        "technical": Agent(name="Technical", role=AgentRole.ASSISTANT, goal="技术支持", backstory="技术专家"),
        "manager": Agent(name="Manager", role=AgentRole.ASSISTANT, goal="管理", backstory="经理")
    }
    
    handoff_manager = HandoffManager(Path("."))
    
    # 模拟多次交接
    handoffs = [
        ("triage", "billing", "账单查询"),
        ("billing", "manager", "复杂账单争议"),
        ("triage", "technical", "软件故障"),
        ("technical", "manager", "技术升级")
    ]
    
    for from_name, to_name, reason in handoffs:
        await handoff_manager.execute_handoff(
            from_agent=agents[from_name],
            to_agent=agents[to_name],
            message=reason,
            context={"history": []}
        )
    
    # 查看交接历史
    history = handoff_manager.get_handoff_history()
    
    print(f"交接历史记录 ({len(history)} 次交接):")
    print("-" * 60)
    for i, record in enumerate(history, 1):
        print(f"{i}. {record['from']} → {record['to']}")
        print(f"   原因: {record['message']}")
        print(f"   时间: {record['timestamp']}")
        print(f"   上下文: {record['context_summary']}")
        print()


async def main():
    """运行所有示例"""
    print("\n" + "🔄"*30)
    print("Agent Handoffs (代理交接) 示例")
    print("🔄"*30)
    
    await example_1_basic_handoff()
    await example_2_handoff_with_callback()
    await example_3_handoff_history()
    
    print("\n" + "="*60)
    print("所有示例完成!")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
