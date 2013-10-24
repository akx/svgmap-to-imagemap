# -- encoding: utf-8 --
from __future__ import with_statement
import argparse
import os
import subprocess
import Image
import lxml.etree as ET
import tempfile

def parse_color(color):
	return (
		int(color[1:3], 16),
		int(color[3:5], 16),
		int(color[5:7], 16)
	)

MAP_TEST_TEMPLATE = file("map_test_template.html", "rb").read()

class Processor(object):
	def __init__(self,
	             inkscape_path, input_file, output_path, width, height,
	             inactive_fill_color, active_fill_color, inactive_stroke_color):
		self.width = width
		self.height = height
		self.inkscape_path = inkscape_path
		self.input_file = input_file
		self.output_path = output_path
		self.inactive_fill_color = inactive_fill_color
		self.active_fill_color = active_fill_color
		self.inactive_stroke_color = inactive_stroke_color

	def run_export(self, input_file, output_file):
		export_command_line = [
			self.inkscape_path,
		    "-w", str(self.width),
		    "-h", str(self.height),
		    "-e", output_file,
		    input_file,
		]
		subprocess.check_call(export_command_line)

	def export_tree(self, input_tree, output_name):
		tmp_svg = tempfile.mktemp(".svg")
		with file(tmp_svg, "wb") as outf:
			outf.write(ET.tostring(input_tree, encoding="UTF-8", pretty_print=True))
		self.run_export(tmp_svg, output_name)
		os.unlink(tmp_svg)
		return output_name

	def clean_polys(self):
		for poly in self.polys:
			style = "fill:%s;" % self.inactive_fill_color
			if self.inactive_stroke_color:
				style += "stroke:%s;stroke-width:1px" % self.inactive_stroke_color
			poly.attrib["style"] = style

	def read_file(self, input_file):
		self.tree = ET.parse(input_file)
		self.polys = self.tree.findall("//{http://www.w3.org/2000/svg}polygon") + self.tree.findall("//{http://www.w3.org/2000/svg}path")

	def _create_active_images(self):
		self.poly_areas = {}
		for poly in self.polys:
			self.clean_polys()
			poly.attrib["style"] = "fill:%s" % self.active_fill_color
			id = poly.attrib["id"]
			ac_output = "%s/ac_%s.png" % (self.output_path, id)
			self.export_tree(self.tree, ac_output)
			self.poly_areas[id] = self.find_active_area(ac_output)

	def generate_imagemap_html(self, map_name):
		map_tree = ET.Element("map", {"name": map_name})
		for id, bbox in sorted(self.poly_areas.iteritems()):
			coords = "%d,%d,%d,%d" % bbox
			map_tree.append(ET.Element("area", {
			"shape": "rect",
			"coords": coords,
			"href": "#",
			"onclick": "mapAction('%s', 'click', '%s');return false" % (map_name, id),
			"onmouseover": "mapAction('%s', 'hover', '%s')" % (map_name, id),
			"onmouseout": "mapAction('%s', 'unhover', '%s')" % (map_name, id),
			}))
		return ET.tostring(map_tree, encoding="UTF-8", pretty_print=True)

	def process(self):
		self.read_file(self.input_file)
		self.clean_polys()
		self.export_tree(self.tree, "%s/ia.png" % self.output_path)
		self._create_active_images()
		map_name = "map"
		map_fragment = self.generate_imagemap_html(map_name)
		with file("%s/map_fragment.html" % self.output_path, "wb") as map_outf:
			map_outf.write(map_fragment)
		with file("%s/map_test.html" % self.output_path, "wb") as map_outf:
			map_outf.write(MAP_TEST_TEMPLATE % {
				"map_fragment": map_fragment,
			    "map_name": map_name
			})


	def find_active_area(self, image_file):
		seek_color = parse_color(self.active_fill_color)
		img = Image.open(image_file).convert("RGBA")
		w, h = img.size
		pa = img.load()
		for y in xrange(h):
			for x in xrange(w):
				if pa[x, y][:3] == seek_color:
					pa[x, y] = (255, 0, 0, 255)
				else:
					pa[x, y] = (0, 0, 0, 0)
		return img.getbbox()


def cmdline():
	ap = argparse.ArgumentParser()
	ap.add_argument("--inkscape-path", default="/programs/inkscape/inkscape.com")
	ap.add_argument("--inactive-fill-color", default='#f5f5f5')
	ap.add_argument("--inactive-stroke-color", default='#666666')
	ap.add_argument("--active-fill-color", default='#078a01')
	ap.add_argument("--input-file", default="maakunnat.svg")
	ap.add_argument("--output-path", default="test")
	ap.add_argument("--width", type=int, default=228)
	ap.add_argument("--height", type=int, default=400)
	args = ap.parse_args()
	p = Processor(**vars(args))
	p.process()

if __name__ == "__main__":
	cmdline()