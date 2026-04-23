from __future__ import annotations

import ast
from typing import Callable, Dict

import sympy as sp


_ALLOWED_CONSTANTS: Dict[str, sp.Expr] = {
    'e': sp.E,
    'E': sp.E,
    'pi': sp.pi,
}
_ALLOWED_FUNCTIONS: Dict[str, Callable[..., sp.Expr]] = {
    'abs': sp.Abs,
    'cos': sp.cos,
    'exp': sp.exp,
    'log': sp.log,
    'sin': sp.sin,
    'sqrt': sp.sqrt,
    'tan': sp.tan,
}


def calculator_tool(expression: str) -> str:
    normalized = expression.strip()
    if not normalized:
        return '计算错误：表达式不能为空。'

    try:
        parsed = ast.parse(normalized.replace('^', '**'), mode='eval')
        result = sp.simplify(_convert_node(parsed.body))
        if result.has(sp.zoo, sp.nan) or result.is_infinite:
            return '计算错误：表达式结果不是有限实数。'
        return str(result)
    except Exception as exc:  # noqa: BLE001 - tool must never crash the service
        return f'计算错误：{exc}'


def _convert_node(node: ast.AST) -> sp.Expr:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError('只支持数字常量。')
        return sp.Integer(node.value) if isinstance(node.value, int) else sp.Float(node.value)

    if isinstance(node, ast.Name):
        if node.id in _ALLOWED_CONSTANTS:
            return _ALLOWED_CONSTANTS[node.id]
        if not node.id.isidentifier():
            raise ValueError('变量名不合法。')
        return sp.Symbol(node.id)

    if isinstance(node, ast.BinOp):
        left = _convert_node(node.left)
        right = _convert_node(node.right)
        operator = node.op
        if isinstance(operator, ast.Add):
            return left + right
        if isinstance(operator, ast.Sub):
            return left - right
        if isinstance(operator, ast.Mult):
            return left * right
        if isinstance(operator, ast.Div):
            return left / right
        if isinstance(operator, ast.Pow):
            return left**right
        if isinstance(operator, ast.Mod):
            return left % right
        raise ValueError('暂不支持该运算符。')

    if isinstance(node, ast.UnaryOp):
        operand = _convert_node(node.operand)
        if isinstance(node.op, ast.UAdd):
            return operand
        if isinstance(node.op, ast.USub):
            return -operand
        raise ValueError('暂不支持该一元运算。')

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError('只支持简单函数调用。')
        function_name = node.func.id
        function = _ALLOWED_FUNCTIONS.get(function_name)
        if function is None:
            raise ValueError(f'不支持函数 {function_name}。')
        if node.keywords:
            raise ValueError('暂不支持关键字参数。')
        return function(*[_convert_node(argument) for argument in node.args])

    raise ValueError('表达式包含不支持的语法。')
