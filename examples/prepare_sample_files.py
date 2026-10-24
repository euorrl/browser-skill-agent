"""生成不含用户数据的两张 PNG 测试图；在项目根目录执行，已有文件不覆盖。"""

from pathlib import Path
import struct,zlib
out=Path('files/uploads');out.mkdir(parents=True,exist_ok=True)
def png(w,h,seed):
 def chunk(t,d):return struct.pack('!I',len(d))+t+d+struct.pack('!I',zlib.crc32(t+d)&0xffffffff)
 rows=b''.join(b'\0'+bytes((x*11+y*19+c*73+seed)%256 for x in range(w) for c in range(3)) for y in range(h))
 return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(rows))+chunk(b'IEND',b'')
for name,w,h,s in [('sample-a.png',96,64,3),('sample-b.png',80,120,61)]:
 path = out / name
 if path.exists():
  print(f'保留已有文件：{path}')
 else:
  path.write_bytes(png(w,h,s))
  print(f'已生成测试图：{path}（{w}×{h}）')
