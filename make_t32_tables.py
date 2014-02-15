#!/usr/bin/env/python
"""
    make_t32_tables.py -- Given a list of people involved with the T32
    proposal, make the various tables required by the NIH.

    Version 0.0 MC 2014-02-15
    --  Framing. Sample data -- dept, faculty, predoc, postdoc

    To Do
    --  Input output analysis for each table
    --  Augment proposal data with VIVO data
    --  Formatting for each table

"""

__author__ = "Michael Conlon"
__copyright__ = "Copyright 2014, University of Florida"
__license__ = "BSD 3-Clause license"
__version__ = "0.0"

import vivotools as vt
import datetime
import json
import tempita

# I wish rtf-ng was more organized and we didn't need all the imports below,
# but it isn't and we do.

from rtfng.Renderer import Renderer
from rtfng.Elements import Document, PAGE_NUMBER
from rtfng.Styles import TextStyle, ParagraphStyle
from rtfng.document.section import Section
from rtfng.document.paragraph import Paragraph, Table, Cell
from rtfng.document.character import B, I
from rtfng.PropertySets import MarginsPropertySet, BorderPropertySet, \
    FramePropertySet, TabPropertySet, TextPropertySet, ParagraphPropertySet
from rtfng.document.base import TAB

def find_dept(deptid):
    """
    Given a UF deptid, find the URI of the org that has that deptid
    """
    query = tempita.Template("""
    SELECT ?uri
    WHERE {
        ?uri ufVivo:deptID "{{deptid}}" .
    }
    """)
    query = query.substitute(deptid=deptid)
    result = vt.vivo_sparql_query(query)
    try:
        uri = result['results']['bindings'][0]['uri']['value']
    except:
        uri = None
    return uri

def find_person(ufid):
    """
    Given a UFID, find the URI of the person that has that ufidid
    """
    query = tempita.Template("""
    SELECT ?uri
    WHERE {
        ?uri ufVivo:ufid "{{ufid}}" .
    }
    """)
    query = query.substitute(ufid=ufid)
    result = vt.vivo_sparql_query(query)
    try:
        uri = result['results']['bindings'][0]['uri']['value']
    except:
        uri = None
    return uri

def t32_dept_counts(uri):
    """
    Given a URI of a unit, count five things the NIH wants to know about
    the unit for a T32 application
    """
    query = tempita.Template("""
#
# Count the faculty, graduate students and postdocs in a unit
#
    SELECT
           (COUNT(DISTINCT ?fac) AS ?faculty_count)
           (COUNT(DISTINCT ?pre) AS ?predoc_count)
           (COUNT(DISTINCT ?pos) AS ?postdoc_count)
           (COUNT(DISTINCT ?pre_sup) AS ?predoc_supported)
           (COUNT(DISTINCT ?pos_sup) AS ?postdoc_supported)
    WHERE {
        {
        ?fac ufVivo:homeDept <{{uri}}> .
        ?fac a vivo:FacultyMember .
        }
        UNION {
        ?pre ufVivo:homeDept <{{uri}}> .
        ?pre a vivo:GraduateStudent .
        }
        UNION {
        ?pos ufVivo:homeDept <{{uri}}> .
        ?pos a vivo:Postdoc .
        }
        UNION {
        ?pre_sup ufVivo:homeDept <{{uri}}> .
        ?pre_sup a vivo:GraduateStudent .
        ?pre_sup vivo:hasPrincipalInvestigatorRole ?role .
        ?role vivo:roleIn ?grant .
        ?grant a vivo:Grant .
        }
        UNION {
        ?pos_sup ufVivo:homeDept <{{uri}}> .
        ?pos_sup a vivo:Postdoc .
        ?pos_sup vivo:hasPrincipalInvestigatorRole ?role .
        ?role vivo:roleIn ?grant .
        ?grant a vivo:Grant .
        }
    }
    GROUP BY ?uri
    """)
    query = query.substitute(uri=uri)
    result = vt.vivo_sparql_query(query)
    t32 = {}
    for vname in ['faculty_count', 'predoc_count', 'postdoc_count',
                  'predoc_supported','postdoc_supported']:
        try:
            t32[vname] = \
                result['results']['bindings'][0][vname]['value']
        except:
            pass
    return t32

def t32_dept(dept, faculty, predoc, postdoc):
    """
    Given a dept structure, augment with data from VIVO and calculated values
    """
    new_dept = {}
    for row,d in dept.items():
        deptid = d['DEPTID']
        uri = find_dept(deptid)
        d['label'] = vt.get_vivo_value(uri,"rdfs:label")
        result = t32_dept_counts(uri)
        print d['NAME'],uri,result
        for key in result.keys():
            d[key] = result[key]
        fac_participating = 0
        for fac in faculty.values():
            if fac['DEPTID'] == deptid:
                fac_participating = fac_participating + 1
        d['faculty_participating'] = fac_participating
        pre_participating = 0
        pre_tge = 0
        pre_urm = 0
        pre_disabilities = 0
        pre_disadvantaged = 0
        for pre in predoc.values():
            if pre['DEPTID'] == deptid:
                pre_participating = pre_participating + 1
                if pre['TGE'] == "1":
                    pre_tge = pre_tge + 1
                if pre['URM'] == "1":
                    pre_urm = pre_urm + 1
                if pre['DISABILITIES'] == "1":
                    pre_disabilities = pre_disabilities + 1
                if pre['DISADVANTAGED'] == "1":
                    pre_disadvantaged = pre_disadvantaged + 1
        d['pre_participating'] = pre_participating
        d['pre_tge'] = pre_tge
        d['pre_urm'] = pre_urm
        d['pre_disabilities'] = pre_disabilities
        d['pre_disadvantaged'] = pre_disadvantaged
        pos_participating = 0
        pos_tge = 0
        pos_urm = 0
        pos_disabilities = 0
        pos_disadvantaged = 0
        for pos in postdoc.values():
            if pos['DEPTID'] == deptid:
                pos_participating = pos_participating + 1
                if pos['TGE'] == "1":
                    pos_tge = pos_tge + 1
                if pos['URM'] == "1":
                    pos_urm = pos_urm + 1
                if pos['DISABILITIES'] == "1":
                    pos_disabilities = pos_disabilities + 1
                if pos['DISADVANTAGED'] == "1":
                    pos_disadvantaged = pos_disadvantaged + 1
        d['pos_participating'] = pos_participating
        d['pos_tge'] = pos_tge
        d['pos_urm'] = pos_urm
        d['pos_disabilities'] = pos_disabilities
        d['pos_disadvantaged'] = pos_disadvantaged
        new_dept[row] = d

    return new_dept

def t32_faculty(faculty):
    """
    Given faculty participating in a T32, augment with VIVO data for
    attributes of interest to the NIH
    """
    new_faculty = {}
    for row, f in faculty.items():
        uri = find_person(f['UFID'])
        person = vt.get_person(uri, get_positions=True, get_degrees=True)
        f['rank'] = person['preferred_title']
        f['degrees'] = person['degrees']
        f['positions'] = person['positions']
        new_faculty[row] = f

    return new_faculty

# Start here. Get proposal data.  Setup the document

print "Start", str(datetime.datetime.now())
print "Read data", str(datetime.datetime.now())
data = vt.read_csv("sample_proposal.csv")
print "CSV\n",json.dumps(data,indent=4)
dept = {}
faculty = {}
predoc = {}
postdoc = {}
for row in data.keys():
    type = data[row]["TYPE"]
    if type == "department":
        dept[row] = data[row]
    elif type == "faculty":
        faculty[row] = data[row]
    elif type == "predoc":
        predoc[row] = data[row]
    elif type == "postdoc":
        postdoc[row] = data[row]
    else:
        print "No such type:", type, "on row", row
print "Departments\n", json.dumps(dept, indent=4)
print "Faculty\n", json.dumps(faculty, indent=4)
print "Predoc\n", json.dumps(predoc, indent=4)
print "Postdoc", json.dumps(postdoc, indent=4)

dept = t32_dept(dept, faculty, predoc, postdoc)
print "Department data\n", json.dumps(dept, indent=4)
faculty = t32_faculty(faculty)
print "Faculty data\n", json.dumps(faculty, indent=4)

thin_edge = BorderPropertySet(width=11, style=BorderPropertySet.SINGLE)
topBottom = FramePropertySet(top=thin_edge, bottom=thin_edge)
bottom_frame = FramePropertySet(bottom=thin_edge)
bottom_right_frame = FramePropertySet(right=thin_edge, bottom=thin_edge)
right_frame = FramePropertySet(right=thin_edge)
top_frame = FramePropertySet(top=thin_edge)

doc = Document()
ss = doc.StyleSheet

# Set the margins for the section at 0.5 inch on all sides

ms = MarginsPropertySet(top=720, left=720, right=720, bottom=720)
section = Section(margins=ms, landscape=True)
doc.Sections.append(section)

# Improve the style sheet.  1440 twips to the inch

ps = ParagraphStyle('Title', TextStyle(TextPropertySet(ss.Fonts.Arial, 22,
    bold=True)).Copy(), ParagraphPropertySet(alignment=3, space_before=270,
    space_after=30))
ss.ParagraphStyles.append(ps)
ps = ParagraphStyle('Subtitle', TextStyle(TextPropertySet(ss.Fonts.Arial,
    16)).Copy(), ParagraphPropertySet(alignment=3, space_before=0,
    space_after=0))
ss.ParagraphStyles.append(ps)
ps = ParagraphStyle('SubtitleLeft', TextStyle(TextPropertySet(ss.Fonts.Arial,
    16)).Copy(), ParagraphPropertySet(space_before=0, space_after=0))
ss.ParagraphStyles.append(ps)
ps = ParagraphStyle('Heading 3', TextStyle(TextPropertySet(ss.Fonts.Arial, 22,
    bold=True)).Copy(), ParagraphPropertySet(space_before=180,
    space_after=60, tabs=[TabPropertySet(360)]))
ss.ParagraphStyles.append(ps)
ps = ParagraphStyle('Header', TextStyle(TextPropertySet(ss.Fonts.Arial,
    16)).Copy(), ParagraphPropertySet(left_indent=int((9.0/16.0)*1440),
    space_before=0, space_after=60))
ss.ParagraphStyles.append(ps)
ps = ParagraphStyle('Footer', TextStyle(TextPropertySet(ss.Fonts.Arial,
    16)).Copy(), ParagraphPropertySet(space_before=60, tabs=[\
    TabPropertySet(int(0.5*section.TwipsToRightMargin()),
    alignment=TabPropertySet.CENTER),
    TabPropertySet(int(0.5*section.TwipsToRightMargin()),
    alignment=TabPropertySet.RIGHT)]))
ss.ParagraphStyles.append(ps)

# Put in the header and footer

p = Paragraph(ss.ParagraphStyles.Header)
p.append("Program Director/Principal Investigator (Last, First, Middle): ")
section.Header.append(p)

p = Paragraph(ss.ParagraphStyles.Footer, top_frame)
p.append('PHS 398/2590 (Rev. 06/09)', TAB, 'Page ', PAGE_NUMBER, TAB,
    "Biographical Sketch Format Page")
section.Footer.append(p)

### Put in the top table
##
##table = Table(5310, 270, 1170, 1440, 2610)
##
##p1 = Paragraph(ss.ParagraphStyles.Title, "BIOGRAPHICAL SKETCH")
##p2 = Paragraph(ss.ParagraphStyles.Subtitle)
##p2.append('Provide the following information for the Senior/key personnel ' \
##    'and other significant contributors in the order listed on Form Page 2.')
##p3 = Paragraph(ss.ParagraphStyles.Subtitle)
##p3.append("Follow this format for each person.  ",
##    B("DO NOT EXCEED FOUR PAGES."))
##c = Cell(p1, p2, p3, topBottom, span=5)
##table.AddRow(c)
##
##c = Cell(Paragraph(ss.ParagraphStyles.Subtitle, ' '), bottom_frame, span=5)
##table.AddRow(c)
##
##p1 = Paragraph(ss.ParagraphStyles.SubtitleLeft, 'NAME')
##p2 = Paragraph(ss.ParagraphStyles.Normal, person['first_name'], ' ',
##    person['last_name'])
##c1 = Cell(p1, p2, bottom_right_frame, span=2)
##c2 = Cell(Paragraph(ss.ParagraphStyles.SubtitleLeft, 'POSITION TITLE'), span=3)
##table.AddRow(c1, c2)
##
##p1 = Paragraph(ss.ParagraphStyles.SubtitleLeft,
##    'eRA COMMONS USER NAME (credential, e.g., agency login)')
##p2 = Paragraph(ss.ParagraphStyles.Normal, person['era_commons'])
##c1 = Cell(p1, p2, bottom_right_frame, span=2)
##c2 = Cell(Paragraph(ss.ParagraphStyles.Normal, person['preferred_title']),
##    bottom_frame, span=3)
##table.AddRow(c1, c2)
##
##c = Cell(Paragraph(ss.ParagraphStyles.SubtitleLeft, "EDUCATION/TRAINING  ",
##    I('(Begin with baccalaureate or other initial professional education,'
##    ' such as nursing, include postdoctoral training and residency training'
##    ' if applicable.)')), bottom_frame, span=5)
##table.AddRow(c)
##
##c1 = Cell(Paragraph(ss.ParagraphStyles.Subtitle, 'INSTITUTION AND LOCATION'),
##    bottom_right_frame, alignment=Cell.ALIGN_CENTER)
##p1 = Paragraph(ss.ParagraphStyles.Subtitle, 'DEGREE')
##p2 = Paragraph(ss.ParagraphStyles.Subtitle, I('(if applicable)'))
##c2 = Cell(p1, p2, bottom_right_frame, span=2)
##c3 = Cell(Paragraph(ss.ParagraphStyles.Subtitle, 'MM/YY'),
##    bottom_right_frame, alignment=Cell.ALIGN_CENTER)
##c4 = Cell(Paragraph(ss.ParagraphStyles.Subtitle, 'FIELD OF STUDY'),
##    bottom_frame, alignment=Cell.ALIGN_CENTER)
##table.AddRow(c1, c2, c3, c4)
##
### The degrees
##
##degrees = {}
##for degree in person['degrees']:
##    key = degree['end_date']['date']['year']+degree['major_field']
##    degrees[key] = degree
##last_degree = min(5, len(degrees))
##ndegree = 0
##for key in sorted(degrees.keys(), reverse=True):
##    ndegree = ndegree + 1
##    degree = degrees[key]
##    if ndegree < last_degree:
##        c1 = Cell(Paragraph(ss.ParagraphStyles.Normal, \
##            degree['institution_name']), right_frame)
##        c2 = Cell(Paragraph(ss.ParagraphStyles.Normal, \
##            degree['degree_name']), right_frame, span=2)
##        c3 = Cell(Paragraph(ss.ParagraphStyles.Normal, \
##            degree['end_date']['date']['year']), right_frame)
##        c4 = Cell(Paragraph(ss.ParagraphStyles.Normal, degree['major_field']))
##        table.AddRow(c1, c2, c3, c4)
##    else:
##        c1 = Cell(Paragraph(ss.ParagraphStyles.Normal, \
##            degree['institution_name']), bottom_right_frame)
##        c2 = Cell(Paragraph(ss.ParagraphStyles.Normal, \
##            degree['degree_name']), bottom_right_frame, span=2)
##        c3 = Cell(Paragraph(ss.ParagraphStyles.Normal,
##            degree['end_date']['date']['year']), bottom_right_frame)
##        c4 = Cell(Paragraph(ss.ParagraphStyles.Normal, degree['major_field']), \
##            bottom_frame)
##        table.AddRow(c1, c2, c3, c4)
##        break
##
##section.append(table)
##
### Put in the note
##
##p = Paragraph(ss.ParagraphStyles.Heading3)
##p.append('NOTE: The Biographical Sketch may not exceed four pages.'
##         ' Follow the formats and instructions below.')
##section.append(p)
##
### Section A -- Personal Statemeent
##
##p = Paragraph(ss.ParagraphStyles.Heading3)
##p.append("A.", TAB, "Personal Statement")
##section.append(p)
##p = Paragraph(ss.ParagraphStyles.Normal)
##p.append(person['overview'])
##section.append(p)
##
### Section B -- Positions and Honors
##
##p = Paragraph(ss.ParagraphStyles.Heading3)
##p.append("B.", TAB, "Positions and Honors")
##section.append(p)
##
##positions = {}
##for position in person['positions']:
##    if 'start_date' in position and 'position_label' in position:
##        key = position['start_date']['date']['year']+position['position_label']
##        positions[key] = position
##last_position = min(20, len(positions))
##npos = 0
##for key in sorted(positions.keys(), reverse=True):
##    npos = npos + 1
##    if npos > last_position:
##        break
##    position = positions[key]
##    para_props = ParagraphPropertySet(tabs=[TabPropertySet(550),
##        TabPropertySet(125), TabPropertySet(600)])
##    para_props.SetFirstLineIndent(-1275)
##    para_props.SetLeftIndent(1275)
##    p = Paragraph(ss.ParagraphStyles.Normal, para_props)
##    if 'end_date' in position:
##        p.append(position['start_date']['date']['year'], TAB, '-', TAB,
##            position['end_date']['date']['year'], TAB,
##            position['position_label'], ', ', position['org_name'])
##    else:
##        p.append(position['start_date']['date']['year'], TAB, '-', TAB,
##            TAB, position['position_label'], ', ', position['org_name'])
##    section.append(p)
##
### Section C -- Selected Peer-reviewed Publications
##
##p = Paragraph(ss.ParagraphStyles.Heading3)
##p.append("C.", TAB, "Selected Peer-reviewed Publications")
##section.append(p)
##
##publications = {}
##for pub in person['publications']:
##    if 'date' in pub and 'publication_type' in pub and \
##    pub['publication_type'] == 'academic-article':
##        key = pub['date']['year']+pub['title']
##        publications[key] = pub
##last_pub = min(25, len(publications))
##npub = 0
##for key in sorted(publications.keys(), reverse=True):
##    npub = npub + 1
##    if npub > last_pub:
##        break
##    pub = publications[key]
##    para_props = ParagraphPropertySet()
##    para_props.SetFirstLineIndent(-720)
##    para_props.SetLeftIndent(720)
##    p = Paragraph(ss.ParagraphStyles.Normal, para_props)
##    p.append(str(npub), ". ", vt.string_from_document(pub))
##    section.append(p)
##
### Section D -- Research Support
##
##p = Paragraph(ss.ParagraphStyles.Heading3)
##p.append("D.", TAB, "Research Support")
##section.append(p)
##
##grants = {}
##print person['grants']
##for grant in person['grants']:
##    if 'end_date' in grant and 'title' in grant and \
##    datetime.datetime(int(grant['end_date']['date']['year']),
##        int(grant['end_date']['date']['month']),
##        int(grant['end_date']['date']['day'])) + \
##        datetime.timedelta(days=3*365) > datetime.datetime.now():
##        key = grant['end_date']['date']['year']+grant['title']
##        grants[key] = grant
##print grants
##for key in sorted(grants.keys(), reverse=True):
##    grant = grants[key]
##    para_props = ParagraphPropertySet()
##    para_props.SetFirstLineIndent(-720)
##    para_props.SetLeftIndent(720)
##    p = Paragraph(ss.ParagraphStyles.Normal, para_props)
##    if 'role' in grant and grant['role'] == 'pi':
##        grant_role = 'Principal Investigator'
##    elif 'role' in grant and grant['role'] == 'coi':
##        grant_role = 'Co-investigator'
##    elif 'role' in grant and grant['role'] == 'inv':
##        grant_role = 'Investigator'
##    else:
##        grant_role = ''
##    p.append(grant['start_date']['datetime'][0:10], ' - ',
##        grant['end_date']['datetime'][0:10], ', ', grant['title'], ', ',
##        grant['awarded_by'], ', ', grant['sponsor_award_id'], ', ', grant_role)
##    section.append(p)
##
# All Done.  Write the file

Renderer().Write(doc, file("t32_tables.rtf", "w"))
print str(datetime.datetime.now())
