import re


# 使用示例
latex_code = r'''\begin{array} {r} {{{\\cal L}\_{\\mathrm{I n B}} \\ ( Q, P^{+}, P^{-} )=\\frac{1} {2 | Q |} \\left( \\sum\_{i}^{| Q |} \\sum\_{p^{-}}^{P^{-}} {\\cal L}\_{\\mathrm{P a i r}} \\left( Q\_{i}, P\_{i}^{+}, p^{-} \\right)}} \\\\ {{+\\sum\_{i}^{| Q |} \\sum\_{p^{+}}^{P^{+}} {\\cal L}\_{\\mathrm{P a i r}} \\left( Q\_{i}, P\_{i}^{+}, p^{+} \\right) \\right)}} \\\\ \\end{array}'''
# 写一个函数，修复上面 latex 表达式中存在的问题
def fix_latex_syntax(latex_code):
    # 修复花括号问题
    latex_code = latex_code.replace('{', '\\{').replace('}', '\\}')
    # 修复下标问题
    latex_code = re.sub(r'\\sum\_{(\\w+)}', r'\\sum\_{\\\1}', latex_code)
    return latex_code

fixed_code = fix_latex_syntax(latex_code)
print(fixed_code)