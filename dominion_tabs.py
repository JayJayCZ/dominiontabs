import re,pprint
from optparse import OptionParser
import os.path

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER,A4,portrait,landscape
from reportlab.lib.units import cm,inch
from reportlab.platypus import Frame,Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

def split(l,n):
    i = 0
    while i < len(l) - n:
        yield l[i:i+n]
        i += n
    yield l[i:]

class Card:
    def __init__(self,name,cardset,types,cost,description,potcost=0):
        self.name = name
        self.cardset = cardset
        self.types = types
        self.cost = cost
        self.potcost = potcost
        self.description = description
        self.extra = ""

    def __repr__(self):
        return '"' + self.name + '"'

    def toString(self):
        return self.name + ' ' + self.cardset + ' ' + '-'.join(self.types) + ' ' + `self.cost` + ' ' + self.description + ' ' + self.extra

class DominionTabs:
    labelImages = {
        ('Action',) : 'action.png',
        ('Action','Attack') : 'action.png',
        ('Action','Attack','Prize') : 'action.png',
        ('Action','Reaction') : 'reaction.png',
        ('Action','Victory') : 'action-victory.png',
        ('Action','Duration') : 'duration.png',
        ('Action','Prize') : 'action.png',
        ('Reaction',) : 'reaction.png',
        ('Treasure',) : 'treasure.png',
        ('Treasure','Victory') : 'treasure-victory.png',
        ('Treasure','Prize') : 'treasure.png',
        ('Victory',) : 'victory.png',
        ('Curse',) : 'curse.png'
        }
    
    def drawTab(self,card,x,y,useExtra=False):
    #rightSide = False
        if self.numTabsHorizontal == 2:
            rightSide = x%2 == 1
        else:
            rightSide = useExtra
        self.canvas.resetTransforms()
        self.canvas.translate(self.horizontalMargin,self.verticalMargin)
        if useExtra:
            self.canvas.translate(self.options.back_offset,0)
        self.canvas.translate(x*self.tabWidth,y*self.tabTotalHeight)
    
        #draw outline
        #don't draw outline on back, in case lines don't line up with front
        if not useExtra:
            self.canvas.saveState()
            self.canvas.setLineWidth(0.1)
            if rightSide and not self.options.sameside:
                self.canvas.translate(self.tabWidth,0)
                self.canvas.scale(-1,1)
            self.canvas.lines(self.tabOutline)
            self.canvas.restoreState()

        #draw tab flap
        self.canvas.saveState()
        if not rightSide or self.options.sameside:
            self.canvas.translate(self.tabWidth-self.tabLabelWidth,
                        self.tabTotalHeight-self.tabLabelHeight)
        else:
            self.canvas.translate(0,self.tabTotalHeight-self.tabLabelHeight)
        self.canvas.drawImage(DominionTabs.labelImages[card.types],1,0,
                    self.tabLabelWidth-2,self.tabLabelHeight-1,
                    preserveAspectRatio=False,anchor='n')
        if card.types[0] == 'Treasure' or card.types == ('Curse',):
            textHeight = self.tabLabelHeight/2-4
            costHeight = textHeight
            potSize = 12
            potHeight = 5
        else:
            textHeight = self.tabLabelHeight/2-7
            costHeight = textHeight-1
            potSize = 11
            potHeight = 2

        textInset = 22
        textWidth = 85

        if card.potcost:
            self.canvas.drawImage("potion.png",21,potHeight,potSize,potSize,preserveAspectRatio=True,mask=[255,255,255,255,255,255])
            textInset += potSize
            textWidth -= potSize

        self.canvas.setFont('MinionPro-Bold',12)
        cost = str(card.cost)
        if 'Prize' in card.types:
            cost += '*'
        self.canvas.drawCentredString(12,costHeight,cost)
        fontSize = 12
        name = card.name.upper()
        name_parts = name.split()
        width = pdfmetrics.stringWidth(name,'MinionPro-Regular',fontSize)
        while width > textWidth and fontSize > 8:
            fontSize -= 1
            #print 'decreasing font size for tab of',name,'now',fontSize
            width = pdfmetrics.stringWidth(name,'MinionPro-Regular',fontSize)
        tooLong = width > textWidth
        #if tooLong:
        #    print name

        #self.canvas.drawString(tabLabelWidth/2+8,tabLabelHeight/2-7,name[0])
        w = 0
        for i,n in enumerate(name_parts):
            self.canvas.setFont('MinionPro-Regular',fontSize)
            h = textHeight
            if tooLong:
                if i == 0:
                    h += h/2
                else:
                    h -= h/2
            self.canvas.drawString(textInset+w,h,n[0])
            w += pdfmetrics.stringWidth(n[0],'MinionPro-Regular',fontSize)
            #self.canvas.drawString(tabLabelWidth/2+8+w,tabLabelHeight/2-7,name[1:])
            self.canvas.setFont('MinionPro-Regular',fontSize-2)
            self.canvas.drawString(textInset+w,h,n[1:])
            w += pdfmetrics.stringWidth(n[1:],'MinionPro-Regular',fontSize-2)
            w += pdfmetrics.stringWidth(' ','MinionPro-Regular',fontSize)
            if tooLong:
                w = 0
        self.canvas.restoreState()

        #draw text
        if useExtra and card.extra:
            usingExtra = True
            descriptions = (card.extra,)
        else:
            usingExtra = False
            descriptions = re.split("--+",card.description)
        height = 0
        for d in descriptions:
            if not usingExtra:
            #d = re.sub(r"\n",";",d,flags=re.MULTILINE)
                d = re.sub(r"([^ ;])\+",r"\1; +",d)
            s = getSampleStyleSheet()['BodyText']
            s.fontName = "Times-Roman"
            p = Paragraph(d,s)
            textHeight = self.tabTotalHeight - self.tabLabelHeight + 0.2*cm
            textWidth = self.tabWidth - cm

            w,h = p.wrap(textWidth,textHeight)
            while h > textHeight:
                s.fontSize -= 1
                s.leading -= 1
                #print 'decreasing fontsize on description for',card.name,'now',s.fontSize
                p = Paragraph(d,s)
                w,h = p.wrap(textWidth,textHeight)
            p.drawOn(self.canvas,cm/2.0,textHeight-height-h-0.5*cm)
            height += h + 0.2*cm

    def read_card_extras(self,fname,cards):
        f = open(fname)
        cardName = re.compile("^:::(?P<name>[ \w']*)")
        extras = {}
        currentCard = ""
        extra = ""
        for line in f:
            m = cardName.match(line)        
            if m:
                if currentCard:
                    #print 'found',currentCard
                    #print extra
                    #print '------------------'
                    extras[currentCard] = extra
                currentCard = m.groupdict()["name"]
                extra = ""
            else:
                extra += line
        if currentCard and extra:
            extras[currentCard] = extra
        for c in cards:
            if not c.name in extras:
                print c.name + ' missing from extras'
            else:
                c.extra = extras[c.name]
                #print c.name + ' ::: ' + extra

    def read_card_defs(self,fname):
        cards = []
        f = open(fname)
        carddef = re.compile("^\d+\t+(?P<name>[\w' ]+)\t+(?P<set>\w+)\t+(?P<type>[-\w ]+)\t+\$(?P<cost>\d+)( (?P<potioncost>\d)+P)?\t+(?P<description>.*)")
        currentCard = None
        for line in f:
            m = carddef.match(line)
            if m:
                if m.groupdict()["potioncost"]:
                    potcost = int(m.groupdict()["potioncost"])
                else:
                    potcost = 0
                currentCard = Card(m.groupdict()["name"],
                                   m.groupdict()["set"].lower(),
                                   tuple([t.strip() for t in m.groupdict()["type"].split("-")]),
                                   int(m.groupdict()["cost"]),
                                   m.groupdict()["description"],
                                   potcost)
                cards.append(currentCard)
            elif line.strip():
                if not currentCard.description.strip().endswith(';')\
                        and not currentCard.description.strip().endswith('.')\
                        and not currentCard.description.strip().endswith('---')\
                        and not line.startswith('---'):
                    #print currentCard.description
                    #print line
                    currentCard.description += '; ' + line
                else:
                    currentCard.description += line
            #print currentCard
            #print '----'
        return cards

    def drawCards(self,cards):
        cards = split(cards,self.numTabsVertical*self.numTabsHorizontal)
        for pageCards in cards:
            #print 'pageCards:',pageCards
            for i,card in enumerate(pageCards):       
                #print card
                x = i % self.numTabsHorizontal
                y = i / self.numTabsHorizontal
                self.canvas.saveState()
                self.drawTab(card,x,self.numTabsVertical-1-y)
                self.canvas.restoreState()
            self.canvas.showPage()
            for i,card in enumerate(pageCards):       
                #print card
                x = (self.numTabsHorizontal-1-i) % self.numTabsHorizontal
                y = i / self.numTabsHorizontal
                self.canvas.saveState()
                self.drawTab(card,x,self.numTabsVertical-1-y,useExtra=True)
                self.canvas.restoreState()
            self.canvas.showPage()

    def main(self,argstring):
        parser = OptionParser()
        parser.add_option("--back_offset",type="int",dest="back_offset",default=5,
                          help="Points to offset the back page to the right; needed for some printers")
        parser.add_option("--orientation",type="string",dest="orientation",default="horizontal",
                          help="horizontal or vertical, default:horizontal")
        parser.add_option("--sleeved",action="store_true",dest="sleeved",help="use --size=sleeved instead")
        parser.add_option("--size",type="string",dest="size",default='normal',
                          help="'<%f>x<%f>' (size in cm), or 'normal' = '9.1x5.9', or 'sleeved' = '9.4x6.15'")
        parser.add_option("--minmargin",type="string",dest="minmargin",default="1x1",
                          help="'<%f>x<%f>' (size in cm, left/right, top/bottom), default: 1x1")
        parser.add_option("--papersize",type="string",dest="papersize",default=None,
                          help="'<%f>x<%f>' (size in cm), or 'A4', or 'LETTER'")
        parser.add_option("--samesidelabels",action="store_true",dest="sameside",
                          help="force all label tabs to be on the same side")
        parser.add_option("--expansions",action="append",type="string",
                          help="subset of dominion expansions to produce tabs for")
        (self.options,args) = parser.parse_args(argstring)

        size = self.options.size.upper()
        if size == 'SLEEVED' or self.options.sleeved:
            dominionCardWidth, dominionCardHeight = (9.4*cm, 6.15*cm)
            print 'Using sleeved card size, %.2fcm x %.2fcm' % (dominionCardWidth/cm,dominionCardHeight/cm)
        elif size == 'NORMAL':
            dominionCardWidth, dominionCardHeight = (9.1*cm, 5.9*cm)
            print 'Using normal card size, %.2fcm x%.2fcm' % (dominionCardWidth/cm,dominionCardHeight/cm)
        else:
            x, y = size.split ("X", 1)
            dominionCardWidth, dominionCardHeight = (float (x) * cm, float (y) * cm)
            print 'Using custom card size, %.2fcm x %.2fcm' % (dominionCardWidth/cm,dominionCardHeight/cm)

        papersize = None
        if not self.options.papersize:
            if os.path.exists("/etc/papersize"):
                papersize = open ("/etc/papersize").readline().upper()
        else:
            papersize = self.options.papersize.upper()

        if papersize == 'A4':
            print "Using A4 sized paper."
            paperwidth, paperheight = A4
        else:
            print "Using letter sized paper."
            paperwidth, paperheight = LETTER

        minmarginwidth, minmarginheight = self.options.minmargin.split ("x", 1)
        minmarginwidth, minmarginheight = float (minmarginwidth) * cm, float (minmarginheight) * cm

        if self.options.orientation == "vertical":
            self.tabWidth, self.tabBaseHeight = dominionCardHeight, dominionCardWidth
        else:
            self.tabWidth, self.tabBaseHeight = dominionCardWidth, dominionCardHeight

        self.tabLabelHeight = 0.9*cm
        self.tabLabelWidth = 3.5*cm
        self.tabTotalHeight = self.tabBaseHeight + self.tabLabelHeight

        numTabsVerticalP = int ((paperheight - 2*minmarginheight) / self.tabTotalHeight)
        numTabsHorizontalP = int ((paperwidth - 2*minmarginwidth) / self.tabWidth)
        numTabsVerticalL = int ((paperwidth - 2*minmarginwidth) / self.tabWidth)
        numTabsHorizontalL = int ((paperheight - 2*minmarginheight) / self.tabTotalHeight)

        if numTabsVerticalL * numTabsHorizontalL > numTabsVerticalP * numTabsHorizontalP:
            self.numTabsVertical, self.numTabsHorizontal\
                = numTabsVerticalL, numTabsHorizontalL
            paperheight, paperwidth = paperwidth, paperheight
        else:
            self.numTabsVertical, self.numTabsHorizontal\
                = numTabsVerticalP, numTabsHorizontalP

        self.horizontalMargin = (paperwidth-self.numTabsHorizontal*self.tabWidth)/2
        self.verticalMargin = (paperheight-self.numTabsVertical*self.tabTotalHeight)/2

        print "Margins: %fcm h, %fcm v\n" % (self.horizontalMargin / cm, 
                                             self.verticalMargin / cm)

        self.tabOutline = [(0,0,self.tabWidth,0),
                      (self.tabWidth,0,self.tabWidth,self.tabTotalHeight),
                      (self.tabWidth,self.tabTotalHeight,
                       self.tabWidth-self.tabLabelWidth,self.tabTotalHeight),
                      (self.tabWidth-self.tabLabelWidth,
                       self.tabTotalHeight,self.tabWidth-self.tabLabelWidth,
                       self.tabBaseHeight),
                      (self.tabWidth-self.tabLabelWidth,
                       self.tabBaseHeight,0,self.tabBaseHeight),
                      (0,self.tabBaseHeight,0,0)]

        try:
            pdfmetrics.registerFont(TTFont('MinionPro-Regular','MinionPro-Regular.ttf'))
            pdfmetrics.registerFont(TTFont('MinionPro-Bold','MinionPro-Bold.ttf'))
        except:
            pdfmetrics.registerFont(TTFont('MinionPro-Regular','OptimusPrincepsSemiBold.ttf'))
            pdfmetrics.registerFont(TTFont('MinionPro-Bold','OptimusPrinceps.ttf'))
        cards = self.read_card_defs("dominion_cards.txt")
        if self.options.expansions:
            self.options.expansions = [o.lower() for o in self.options.expansions]
            cards=[c for c in cards if c.cardset in self.options.expansions]
        cards.sort(cmp=lambda x,y: cmp((x.cardset,x.name),(y.cardset,y.name)))
        extras = self.read_card_extras("dominion_card_extras.txt",cards)
        #print '%d cards read' % len(cards)
        sets = {}
        types = {}
        for c in cards:
            sets[c.cardset] = sets.get(c.cardset,0) + 1
            types[c.types] = types.get(c.types,0) + 1
        #pprint.pprint(sets)
        #pprint.pprint(types)

        if args:
            fname = args[0]
        else:
            fname = "dominion_tabs.pdf"
        self.canvas = canvas.Canvas(fname, pagesize=(paperwidth, paperheight))
        #pprint.pprint(self.canvas.getAvailableFonts())
        self.drawCards(cards)
        self.canvas.save()
    
if __name__=='__main__':
    import sys
    tabs = DominionTabs()
    tabs.main(sys.argv[1:])
