import logging
logging.getLogger('matplotlib').setLevel(logging.WARNING)

import numpy as np

from matplotlib import cm
from matplotlib.colors import to_hex

def get_colors(size, name='Set1'):
  # Available colormap,
  # 'plasma' 'viridis' 'magma' 'cividis' 'inferno' 'Set1'
  try:
    colorm = cm.get_cmap(name, size)
    colors = [ to_hex(c) for c in colorm.colors ]
  except:
    colorm = cm.get_cmap(name)
    vals = np.linspace(0,1,size)
    colors = [ to_hex(colorm(v)) for v in vals ]
  return colors

def df_to_html(df):
  row_class = 'table-primary'

  header = f"""
  <thead>
    <tr>
      <th class="{row_class}">{f'''</th>
      <th class="{row_class}">'''.join(df.columns)}</th>
    </tr>
  </thead>"""

  footer = f"""
  <tfoot>
    <tr class="{row_class}">
      <th>{'''</th>
      <th>'''.join(df.columns)}</th>
    </tr>
  </tfoot>
  """

  data = f"""
  <tbody>"""
  for i, row in df.iterrows():
    data += f"""
    <tr>
      <td>{'''</td>
      <td>'''.join([ str(v) for v in row.values ])}</td>
    </tr>"""
  data += """
  </tbody>"""

  dimensions = f"""
  <p><b>{len(df)} rows × {len(df.columns)} columns</b></p>"""

  content = header + footer + data + dimensions
  return content
