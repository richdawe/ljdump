#!/usr/bin/python

# Copyright 2009, Sean M. Graham (www.sean-graham.com)
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
# 
# - Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
# 
# - Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
# EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. 

import xml.dom.minidom 
import os
import codecs
import sys

from time import strptime, strftime

def getNodeText(doc, nodename):
    rc = ""

    try:
        nodelist = doc.getElementsByTagName(nodename)[0].childNodes
    except:
        return ""

    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc = rc + node.data

    return rc

def appendTextNode(doc, parent, nodename, value):
    nodeValue = value

    # make sure value is properly encoded
    try:
        bytes = nodeValue.encode("UTF-8")
    except:
        bytes = nodeValue.encode("cp1252")
        nodeValue = unicode(bytes, "UTF-8")

    element = doc.createElement(nodename)

    if( nodeValue != "" ): 
        textNode = doc.createTextNode(nodeValue)
        element.appendChild(textNode)

    parent.appendChild(element)


def addEntryForId(outDoc, element, username, id, includeSecure):
    entryFile = open("%s/L-%s" % (username,id), "r")
    inDoc = xml.dom.minidom.parse(entryFile)

    # Create an entry element
    entry = outDoc.createElement("entry")

    # Create an itemid element
    appendTextNode(outDoc, entry, "itemid", getNodeText(inDoc,"itemid"))

    # Create an eventtime element
    appendTextNode(outDoc, entry, "eventtime", getNodeText(inDoc, "eventtime"))

    # Create an subject element
    appendTextNode(outDoc, entry, "subject", getNodeText(inDoc, "subject"))

    # Create an event node (special case because for some reason there are two
    # 'event' elements in the pydump output, which is probably LJ's fault)
    event = inDoc.getElementsByTagName("event")[0]
    appendTextNode(outDoc, entry, "event", getNodeText(event, "event"))

    security = getNodeText(inDoc, "security")

    if(security != ""):
        # don't append this entry unless the user provided the argument
        if(includeSecure == False):
            print("omitting secure entry: L-%s" % id)
            return 
        else:
            if(security == "usemask"):
                print("including allowmask entry: L-%s" % id)

                # Create an allowmask element 
                maskText = getNodeText(inDoc, "allowmask")

                if(maskText != ""):
                    appendTextNode(outDoc, entry, "allowmask", maskText)
                else:
                    appendTextNode(outDoc, entry, "allowmask", "0")
            else:
                print("including private entry: L-%s" % id)

        appendTextNode(outDoc, entry, "security", security)

    # Create a taglist element
    appendTextNode(outDoc, entry, "taglist", getNodeText(inDoc, "taglist"))

    # XXXSMG: make sure there is a comment file before trying to do anything
    # with it
    addCommentsForId(outDoc, entry, username, id)

    element.appendChild(entry)

def addCommentsForId(outDoc, entry, username, id):
    try: 
        commentFile = open("%s/C-%s" % (username,id), "r")
    except IOError:  # there are no comments for this entry
        return

    inDoc = xml.dom.minidom.parse(commentFile)

    comments = inDoc.getElementsByTagName("comment")

    for comment in comments:
        outComment = outDoc.createElement("comment")
        entry.appendChild(outComment)

        # add the item id for the comment
        appendTextNode(outDoc, outComment, "itemid", 
            getNodeText(comment, "id"))

        # convert the time string
        timeString = getNodeText(comment, "date")
        if( timeString != "" ):
            inDate = strptime(timeString, "%Y-%m-%dT%H:%M:%SZ")
            outDate = strftime("%Y-%m-%d %H:%M:%S", inDate)
            appendTextNode(outDoc, outComment, "eventtime", outDate)
        else:
            emptyTime = outDoc.createElement("eventtime")
            outComment.appendChild(emptyTime)

        # Create an subject element
        appendTextNode(outDoc, outComment, "subject", 
            getNodeText(comment, "subject"))

        # Create an event element
        appendTextNode(outDoc, outComment, "event", 
            getNodeText(comment, "body"))

        # Create the author element
        author = outDoc.createElement("author")
        outComment.appendChild(author)

        try:
            cUser = getNodeText(comment, "user")
        except:
            cUser = "anonymous"

        appendTextNode(outDoc, author, "name", cUser)
        appendTextNode(outDoc, author, "email", cUser + "@livejournal.com")
        
        # Create the parent_itemid
        parentId = getNodeText(comment, "parentid")
        if(parentId != ""): 
            appendTextNode(outDoc, outComment, "parent_itemid", parentId)

def main(argv): 
    username = ""
    entryLimit = 250
    includeSecure = False;
    
    if( len(argv) < 2 ):
        print( "Usage: convertdump.py <username> <entrylimit>" )
        return
    else:
        username = argv[0]
        entryLimit = int(argv[1])

        try:
            includeSecure = bool(argv[2])
        except IndexError:
            includeSecure = False

    if(includeSecure == True):
        print( "Warning:  Including secure entries in XML output" )

    userDir = os.listdir(username)

    highNum = -1
    entryArray = []

    # get the list of entries
    for file in userDir:
        if file.startswith("L-"):
            entryNum = int(file.replace("L-",""))

            entryArray.append(entryNum)

            if( highNum < entryNum ):
                highNum = entryNum

    entryArray.sort()

    # Create the minidom document
    outDoc = xml.dom.minidom.Document()

    # Create the <livejournal> base element
    ljElement = outDoc.createElement("livejournal")
    outDoc.appendChild(ljElement)

    currentFileEntry = 0

    # start processing entries
    for entry in entryArray:
        addEntryForId(outDoc, ljElement, username, entry, includeSecure)

        currentFileEntry += 1

        if( currentFileEntry == entryLimit or entry == entryArray[-1] ):

            f = open("%s - %s.xml" % (username, entry), "w")
            tempXML = outDoc.toxml("UTF-8")
            f.write(tempXML)
            
            currentFileEntry = 0

            # Create the minidom document
            outDoc = xml.dom.minidom.Document()

            # Create the <livejournal> base element
            ljElement = outDoc.createElement("livejournal")
            outDoc.appendChild(ljElement)

if __name__ == "__main__":
    main(sys.argv[1:])

